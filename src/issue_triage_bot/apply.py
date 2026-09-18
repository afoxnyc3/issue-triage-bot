"""Comment-first deterministic apply with live fences and resumable signed intent."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Literal, Protocol

from pydantic import Field, ValidationError

from .codec import BoundaryError, decision_hash, parse_json, validate_envelope
from .comment import KeyRing, discover_state, render_comment
from .gate import security_hit
from .github import GitHubError
from .models import (
    Comment,
    CommentState,
    Digest,
    Issue,
    IssueKind,
    Label,
    ProposalEnvelope,
    RunContext,
    StrictModel,
    TriageDecision,
)
from .policy import Intent, LabelEvent, evaluate, reconcile
from .release import LiveRelease, ReleaseReader, load_live


class Gateway(ReleaseReader, Protocol):
    def issue(self, number: int) -> Issue: ...
    def comments(self, number: int) -> tuple[Comment, ...]: ...
    def timeline(self, number: int) -> tuple[LabelEvent, ...]: ...
    def create_comment(self, number: int, body: str) -> int: ...
    def edit_comment(self, number: int, comment_id: int, body: str) -> None: ...
    def add_label(self, number: int, label: str) -> None: ...
    def remove_label(self, number: int, label: str) -> None: ...


class Operation(StrictModel):
    name: Literal["create_comment", "edit_comment", "add_label", "remove_label"]
    label: Label | None = None
    result: Literal["confirmed", "uncertain", "failed", "planned"]


class ApplyRecord(StrictModel):
    audit_version: Literal[1] = 1
    context: RunContext
    envelope: ProposalEnvelope | None = None
    decision_hash: Digest | None = None
    status: Literal[
        "applied",
        "review_sensitive",
        "review_transient",
        "transient",
        "deferred",
        "skip",
        "dry_run",
        "shadow",
        "disabled",
        "rejected",
        "invalid_state",
        "partial",
        "failed",
        "mutation_deferred",
    ]
    before_labels: Annotated[tuple[Label, ...], Field(max_length=100)] | None = None
    after_labels: Annotated[tuple[Label, ...], Field(max_length=100)] | None = None
    state_phase: Literal["pending", "final"] | None = None
    labels_truncated: bool = False
    operations: Annotated[tuple[Operation, ...], Field(max_length=100)] = ()
    recorded_at: str


class FenceError(BoundaryError):
    pass


class LabelChanged(BoundaryError):
    """The planned label mutation became unnecessary before it could execute."""


# A production implementation must make a durable reservation under the global apply slot.
MutationReservation = Callable[[ProposalEnvelope, str, str, int], bool]


class Apply:
    def __init__(
        self,
        github: Gateway,
        keys: KeyRing,
        *,
        reserve_mutation: MutationReservation | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.github = github
        self.keys = keys
        self.reserve_mutation = reserve_mutation
        self.now = now
        self._context: RunContext | None = None
        self._envelope: ProposalEnvelope | None = None
        self._dry_run = True
        self._operations: list[Operation] = []
        self._label_intent: tuple[str, str, CommentState] | None = None

    def _timestamp(self) -> str:
        return self.now().astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _fence(self) -> tuple[LiveRelease, Issue]:
        if self._context is None or self._envelope is None:
            raise FenceError("apply context unavailable")
        live = load_live(self.github)
        if live is None:
            raise FenceError("triage disabled")
        issue = self.github.issue(self._context.issue_number)
        validate_envelope(self._envelope, self._context, issue, live.identity)
        if self._dry_run or live.policy.rollout in {"dry_run", "shadow"}:
            raise FenceError("writes disabled by rollout")
        return live, issue

    def guard(self, operation: str, issue_number: int | None) -> None:
        """Install as the concrete GitHub client's write guard as defense in depth."""
        if (
            self._context is None
            or issue_number != self._context.issue_number
            or operation not in {"create_comment", "edit_comment", "add_label", "remove_label"}
        ):
            raise FenceError("write outside apply scope")
        live, current = self._fence()
        if operation in {"add_label", "remove_label"}:
            if self._label_intent is None or self._label_intent[0] != operation:
                raise FenceError("label intent unavailable")
            _, label, pending = self._label_intent
            found = discover_state(self.github.comments(current.number), current, self.keys)
            if found.unreadable or found.state != pending:
                raise FenceError("pending state changed")
            plan = reconcile(
                current.labels,
                pending.intended_labels,
                policy=live.policy,
                authenticated_state=pending,
                events=self.github.timeline(current.number),
            )
            permitted = plan.add if operation == "add_label" else plan.remove
            if label not in permitted:
                raise LabelChanged("label state changed")

    def _record(
        self,
        status: str,
        before: tuple[str, ...] | None,
        *,
        envelope: ProposalEnvelope | None = None,
        state: CommentState | None = None,
        after: tuple[str, ...] | None = None,
    ) -> ApplyRecord:
        assert self._context is not None
        return ApplyRecord.model_validate(
            {
                "context": self._context,
                "envelope": envelope,
                "decision_hash": state.decision_hash if state else None,
                "status": status,
                "before_labels": before[:100] if before is not None else None,
                "after_labels": after[:100] if after is not None else None,
                "state_phase": state.state if state else None,
                "labels_truncated": (before is not None and len(before) > 100)
                or (after is not None and len(after) > 100),
                "operations": tuple(self._operations),
                "recorded_at": self._timestamp(),
            }
        )

    def _verified_related(
        self, decision: TriageDecision | None, envelope: ProposalEnvelope
    ) -> tuple[tuple[int, str], ...]:
        result: list[tuple[int, str]] = []
        if decision is not None:
            for related in decision.related_issues:
                if (
                    related.number not in envelope.candidates
                    or related.number == envelope.issue_number
                ):
                    raise BoundaryError("unapproved related candidate")
                issue = self.github.issue(related.number)
                if issue.repository != envelope.repository or issue.number != related.number:
                    raise BoundaryError("related candidate identity mismatch")
                result.append((related.number, related.reason))
        return tuple(result)

    def _comment(
        self, state: CommentState, live: LiveRelease, related: tuple[tuple[int, str], ...]
    ) -> str:
        area = live.policy.areas.get(state.decision.area or "") if state.decision else None
        return render_comment(state, self.keys, area_name=area, verified_related=related)

    def _write_comment(self, number: int, body: str, comment_id: int | None) -> int:
        name: Literal["create_comment", "edit_comment"] = (
            "create_comment" if comment_id is None else "edit_comment"
        )
        self.guard(name, number)
        try:
            if comment_id is None:
                comment_id = self.github.create_comment(number, body)
            else:
                self.github.edit_comment(number, comment_id, body)
        except GitHubError as error:
            self._operations.append(
                Operation(name=name, result="uncertain" if error.uncertain else "failed")
            )
            raise
        self._operations.append(Operation(name=name, result="confirmed"))
        return comment_id

    def run(
        self,
        envelope: ProposalEnvelope,
        context: RunContext,
        proposal: bytes | None,
        *,
        dry_run: bool = False,
        force_decision: bool = False,
    ) -> ApplyRecord:
        self._context, self._envelope, self._dry_run = context, envelope, dry_run
        self._operations = []
        before: tuple[str, ...] | None = None
        accepted: ProposalEnvelope | None = None
        pending: CommentState | None = None
        try:
            live = load_live(self.github)
            if live is None:
                return self._record("disabled", before)
            issue = self.github.issue(context.issue_number)
            validate_envelope(envelope, context, issue, live.identity)
            accepted = envelope
            before = issue.labels
            if envelope.mode == "skip":
                return self._record("skip", before, envelope=accepted, after=before)
            found = discover_state(self.github.comments(issue.number), issue, self.keys)
            if found.unreadable:
                # Do not guess which comment owns labels or overwrite unsupported state.
                # Repair/health must surface this explicit, non-retryable human-review outcome.
                return self._record("invalid_state", before, envelope=accepted, after=before)
            previous = found.state
            same_content = (
                previous is not None
                and previous.envelope.content_hash == envelope.content_hash
                and previous.envelope.release == envelope.release
            )
            if (
                same_content
                and previous is not None
                and previous.state == "final"
                and previous.envelope.run_id == context.run_id
                and previous.envelope.run_attempt == context.run_attempt
            ):
                return self._record("skip", before, envelope=accepted, state=previous, after=before)
            if (
                same_content
                and previous is not None
                and previous.state == "final"
                and previous.outcome in {"applied", "review_sensitive", "review_transient"}
                and not force_decision
            ):
                return self._record("skip", before, envelope=accepted, state=previous, after=before)
            sensitive = (
                security_hit(issue, live.policy.security_terms) or envelope.mode == "review_only"
            )
            related: tuple[tuple[int, str], ...] = ()
            if (
                same_content
                and previous is not None
                and previous.state == "pending"
                and not sensitive
            ):
                intent = Intent(
                    previous.outcome,
                    previous.intended_labels,
                    previous.retry_eligible,
                    previous.attempts,
                    previous.decision,
                )
                related = self._verified_related(intent.decision, envelope)
            else:
                decision = None
                if not sensitive and envelope.mode == "propose" and proposal is not None:
                    try:
                        decision = parse_json(TriageDecision, proposal)
                        if decision.kind != IssueKind.SECURITY and decision.priority != "P0":
                            related = self._verified_related(decision, envelope)
                    except BoundaryError:
                        decision, related = None, ()
                attempts = previous.attempts if same_content and previous else 0
                intent = evaluate(
                    live.policy,
                    decision,
                    sensitive=sensitive,
                    deferred=envelope.mode == "deferred",
                    previous_attempts=attempts,
                )
            if (
                same_content
                and previous is not None
                and previous.state == "final"
                and previous.outcome in {"applied", "review_sensitive"}
                and previous.outcome == intent.outcome
                and previous.decision == intent.decision
            ):
                return self._record("skip", before, envelope=accepted, state=previous, after=before)
            canary = live.control.canary
            in_cohort = (
                canary is None
                or canary.first_issue <= issue.number < canary.first_issue + canary.max_issues
            )
            desired = intent.labels if in_cohort else ()
            plan = reconcile(
                issue.labels,
                desired,
                policy=live.policy,
                authenticated_state=previous,
                events=self.github.timeline(issue.number),
            )
            if dry_run or live.policy.rollout in {"dry_run", "shadow"}:
                self._operations = [
                    Operation(name="add_label", label=label, result="planned") for label in plan.add
                ]
                self._operations += [
                    Operation(name="remove_label", label=label, result="planned")
                    for label in plan.remove
                ]
                return self._record(
                    "shadow" if live.policy.rollout == "shadow" else "dry_run",
                    before,
                    envelope=accepted,
                    after=before,
                )
            previous_owned = (
                ()
                if previous is None
                else tuple(
                    sorted(
                        set(
                            (
                                *previous.managed_labels,
                                *previous.previous_managed_labels,
                                *previous.pending_additions,
                            )
                        )
                    )
                )
            )
            # Preserve earlier pending additions on resume; otherwise a successful add
            # followed by a lost response could be mistaken for an unowned legacy label.
            additions = tuple(
                sorted(
                    set(plan.add)
                    | (
                        set(previous.pending_additions) & set(desired)
                        if same_content and previous
                        else set()
                    )
                )
            )
            pending = CommentState(
                state_version=1,
                state="pending",
                outcome=intent.outcome,
                retry_eligible=intent.retry_eligible,
                attempts=intent.attempts,
                written_at=self._timestamp(),
                envelope=envelope,
                decision=intent.decision,
                decision_hash=decision_hash(intent.decision, envelope),
                intended_labels=desired,
                pending_additions=additions,
                managed_labels=plan.managed,
                previous_managed_labels=previous_owned,
            )
            comment_id = self._write_comment(
                issue.number, self._comment(pending, live, related), found.comment_id
            )
            for _ in range(65):
                live, current = self._fence()
                found_now = discover_state(self.github.comments(issue.number), current, self.keys)
                if (
                    found_now.unreadable
                    or found_now.comment_id != comment_id
                    or found_now.state != pending
                ):
                    raise BoundaryError("pending state changed")
                plan = reconcile(
                    current.labels,
                    desired,
                    policy=live.policy,
                    authenticated_state=pending,
                    events=self.github.timeline(issue.number),
                )
                if not plan.add and not plan.remove:
                    # This is the read-back: current labels and latest timeline agree with
                    # intent after preserving human overrides. No human label is claimed.
                    final = CommentState(
                        **(
                            pending.model_dump()
                            | {
                                "state": "final",
                                "applied_at": self._timestamp(),
                                "managed_labels": plan.managed,
                                "pending_additions": (),
                                "previous_managed_labels": (),
                            }
                        )
                    )
                    self._write_comment(
                        issue.number, self._comment(final, live, related), comment_id
                    )
                    return self._record(
                        intent.outcome, before, envelope=accepted, state=final, after=current.labels
                    )
                name: Literal["remove_label", "add_label"] = (
                    "remove_label" if plan.remove else "add_label"
                )
                label = plan.remove[0] if plan.remove else plan.add[0]
                if not in_cohort:
                    return self._record(
                        "mutation_deferred",
                        before,
                        envelope=accepted,
                        state=pending,
                        after=current.labels,
                    )
                if canary is not None and (
                    self.reserve_mutation is None
                    or not self.reserve_mutation(envelope, name, label, canary.max_mutations)
                ):
                    return self._record(
                        "mutation_deferred",
                        before,
                        envelope=accepted,
                        state=pending,
                        after=current.labels,
                    )
                # Reservations can take time. Refresh fences once more before the actual request.
                self._label_intent = (name, label, pending)
                try:
                    self.guard(name, issue.number)
                    if name == "remove_label":
                        self.github.remove_label(issue.number, label)
                    else:
                        self.github.add_label(issue.number, label)
                except LabelChanged:
                    continue
                except GitHubError as error:
                    self._operations.append(
                        Operation(
                            name=name,
                            label=label,
                            result="uncertain" if error.uncertain else "failed",
                        )
                    )
                    raise
                finally:
                    self._label_intent = None
                self._operations.append(Operation(name=name, label=label, result="confirmed"))
            raise BoundaryError("label reconciliation did not converge")
        except GitHubError:
            return self._record(
                "partial" if self._operations else "failed",
                before,
                envelope=accepted,
                state=pending,
            )
        except (BoundaryError, ValidationError):
            return self._record(
                "partial" if self._operations else "rejected",
                before,
                envelope=accepted,
                state=pending,
            )
