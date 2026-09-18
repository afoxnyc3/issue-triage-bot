"""Pure policy and label reconciliation. No GitHub side effects, no model calls."""

from dataclasses import dataclass
from typing import Literal

from .comment import BOT_LOGIN
from .config import CONTROL_LABELS, Policy
from .models import CommentState, IssueKind, PositiveID, StrictModel, TriageDecision


@dataclass(frozen=True)
class Intent:
    outcome: Literal["applied", "review_sensitive", "review_transient", "transient", "deferred"]
    labels: tuple[str, ...]
    retry_eligible: bool
    attempts: int
    decision: TriageDecision | None


def evaluate(
    policy: Policy,
    decision: TriageDecision | None,
    *,
    sensitive: bool,
    deferred: bool = False,
    previous_attempts: int = 0,
) -> Intent:
    if sensitive or (
        decision and (decision.kind == IssueKind.SECURITY or decision.priority == "P0")
    ):
        return Intent("review_sensitive", ("needs-triage-review",), False, 0, None)
    if deferred:
        return Intent("deferred", ("triage-deferred",), True, previous_attempts, None)
    if decision is None:
        attempts = min(previous_attempts + 1, 3)
        if attempts == 3:
            return Intent("review_transient", ("needs-triage-review",), False, attempts, None)
        # A failure always reaches a human queue even while automatic retry is pending.
        return Intent("transient", ("needs-triage-review", "triage-retry"), True, attempts, None)
    labels: tuple[str, ...] = ()
    if policy.rollout == "type_labels":
        labels = tuple(
            sorted(set(policy.type_labels.get(decision.kind, ())) & set(policy.label_allowlist))
        )
    return Intent("applied", labels, False, 0, decision)


class LabelEvent(StrictModel):
    id: PositiveID
    event: Literal["labeled", "unlabeled"]
    label: str
    actor_login: str
    actor_type: str

    @property
    def by_bot(self) -> bool:
        return self.actor_login == BOT_LOGIN and self.actor_type == "Bot"


@dataclass(frozen=True)
class LabelPlan:
    add: tuple[str, ...]
    remove: tuple[str, ...]
    managed: tuple[str, ...]
    human_overrides: tuple[str, ...]


def reconcile(
    current: tuple[str, ...],
    desired: tuple[str, ...],
    *,
    policy: Policy,
    authenticated_state: CommentState | None,
    events: tuple[LabelEvent, ...],
) -> LabelPlan:
    """State must come from HMAC verification. Fetch complete timeline before calling."""
    live = {label.casefold(): label for label in current}
    permitted = {label.casefold() for label in policy.label_allowlist} | CONTROL_LABELS
    removable = permitted | {label.casefold() for label in policy.retired_labels}
    intended = {label.casefold(): label for label in desired if label.casefold() in permitted}
    recorded = set()
    if authenticated_state is not None:
        recorded = {
            label.casefold()
            for label in (
                *authenticated_state.managed_labels,
                *authenticated_state.previous_managed_labels,
                *authenticated_state.pending_additions,
            )
        }
    latest: dict[str, LabelEvent] = {}
    for event in sorted(events, key=lambda item: item.id):
        latest[event.label.casefold()] = event
    add: list[str] = []
    remove: list[str] = []
    managed: list[str] = []
    overrides: list[str] = []
    for key, label in intended.items():
        last = latest.get(key)
        if key in live:
            if key in recorded and last and last.event == "labeled" and last.by_bot:
                managed.append(live[key])
            else:
                overrides.append(live[key])
        elif last and not last.by_bot:
            overrides.append(label)
        else:
            add.append(label)
            managed.append(label)
    for key in recorded - intended.keys():
        last = latest.get(key)
        if key in live and key in removable:
            if last and last.event == "labeled" and last.by_bot:
                remove.append(live[key])
            else:
                overrides.append(live[key])
    return LabelPlan(
        tuple(sorted(add)),
        tuple(sorted(remove)),
        tuple(sorted(managed)),
        tuple(sorted(set(overrides))),
    )
