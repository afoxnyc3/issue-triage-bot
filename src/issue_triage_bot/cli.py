"""Explicit operator/workflow commands. Python never loads OAuth or invokes a model."""

import base64
import binascii
import os
import re
from collections.abc import Callable
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path
from typing import Annotated, ParamSpec, TypeVar

import typer

from .apply import Apply, ApplyRecord
from .codec import (
    BoundaryError,
    canonical_json,
    content_hash,
    decode_json,
    digest_bytes,
    parse_json,
)
from .comment import KeyRing, discover_state
from .config import CONTROL_LABELS, Policy, parse_yaml
from .gate import snapshot
from .github import GitHub, WriteGuard, obj
from .models import Issue, ProposalEnvelope, Release, RunContext
from .release import load_live

app = typer.Typer(pretty_exceptions_enable=False, no_args_is_help=True)
P = ParamSpec("P")
R = TypeVar("R")


def _safe(function: Callable[P, R]) -> Callable[P, R]:
    @wraps(function)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return function(*args, **kwargs)
        except typer.Exit:
            raise
        except BoundaryError as error:
            typer.echo(f"triage: {error}", err=True)
            raise typer.Exit(1) from None
        except Exception:
            # Never dump stack locals, request bodies, environment or validation payloads.
            typer.echo("triage: operation failed; no sensitive details logged", err=True)
            raise typer.Exit(1) from None

    return wrapped


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise BoundaryError(f"missing runtime environment variable: {name}")
    return value


def _client(repository: str, guard: WriteGuard | None = None) -> GitHub:
    return GitHub(repository, _required("GITHUB_TOKEN"), write_guard=guard)


def _keys() -> KeyRing:
    def decode(name: str) -> bytes:
        try:
            return base64.b64decode(_required(name), validate=True)
        except (ValueError, binascii.Error):
            raise BoundaryError("invalid state signing configuration") from None

    current_id = _required("TRIAGE_STATE_HMAC_KEY_ID")
    current = decode("TRIAGE_STATE_HMAC_KEY")
    previous_id = os.environ.get("TRIAGE_STATE_HMAC_PREVIOUS_KEY_ID")
    previous = (
        decode("TRIAGE_STATE_HMAC_PREVIOUS_KEY")
        if os.environ.get("TRIAGE_STATE_HMAC_PREVIOUS_KEY")
        else None
    )
    return KeyRing(current_id, current, previous_id=previous_id, previous_key=previous)


def _read(path: Path, limit: int = 16 * 1024) -> bytes:
    with path.open("rb") as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise BoundaryError("input file exceeds size limit")
    return data


def _integer(value: str) -> int:
    if not re.fullmatch(r"[1-9][0-9]{0,19}", value):
        raise BoundaryError("invalid workflow identifier")
    return int(value)


def _context(issue: Issue, *, dry_run: bool) -> RunContext:
    repository = os.environ.get("GITHUB_REPOSITORY")
    if repository is not None and repository != issue.repository:
        raise BoundaryError("workflow repository mismatch")
    run_id = os.environ.get("GITHUB_RUN_ID")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT")
    if run_id is None or attempt is None:
        if not dry_run:
            raise BoundaryError("writes require trusted workflow context")
        run_id, attempt = "1", "1"
    if not dry_run:
        event_name = _required("GITHUB_EVENT_NAME")
        event = obj(
            decode_json(
                _read(Path(_required("GITHUB_EVENT_PATH")), 2 * 1024 * 1024),
                max_bytes=2 * 1024 * 1024,
            )
        )
        if obj(event.get("repository")).get("full_name") != issue.repository:
            raise BoundaryError("workflow event repository mismatch")
        if event_name == "issues":
            target = obj(event.get("issue"))
            if target.get("number") != issue.number or target.get("node_id") != issue.node_id:
                raise BoundaryError("workflow event issue mismatch")
        elif event_name == "workflow_dispatch":
            number = obj(event.get("inputs")).get("issue_number")
            if not isinstance(number, str) or _integer(number) != issue.number:
                raise BoundaryError("workflow dispatch issue mismatch")
        else:
            raise BoundaryError("unsupported workflow event")
    return RunContext(
        repository=issue.repository,
        issue_number=issue.number,
        node_id=issue.node_id,
        run_id=_integer(run_id),
        run_attempt=_integer(attempt),
    )


def _emit(record: ApplyRecord, audit: Path | None) -> None:
    data = canonical_json(record.model_dump(mode="json")) + b"\n"
    if audit is not None:
        audit.write_bytes(data)
    typer.echo(data.decode("ascii"), nl=False)


@app.command("apply")
@_safe
def apply_command(
    issue: Annotated[int, typer.Option(min=1)],
    repo: Annotated[str, typer.Option(envvar="GITHUB_REPOSITORY")],
    input: Annotated[
        Path | None, typer.Option("--input", help="Decision JSON; omit after failure.")
    ] = None,
    envelope: Annotated[
        Path | None, typer.Option(help="Preflight envelope; required for writes.")
    ] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run/--write")] = True,
    force: Annotated[
        bool, typer.Option(help="Explicitly reclassify an unchanged fixture.")
    ] = False,
    audit: Annotated[Path | None, typer.Option(help="Redacted JSON outcome path.")] = None,
) -> None:
    engines: dict[str, Apply] = {}
    github = _client(repo, lambda operation, number: engines["apply"].guard(operation, number))
    try:
        target = github.issue(issue)
        context = _context(target, dry_run=dry_run)
        live = load_live(github)
        if live is None:
            _emit(
                ApplyRecord(
                    context=context,
                    status="disabled",
                    recorded_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                ),
                audit,
            )
            return
        if envelope is None:
            if not dry_run:
                raise BoundaryError("writes require a preflight envelope")
            candidates = github.related_candidates(target, datetime.now(UTC).date())
            bound = ProposalEnvelope(
                **context.model_dump(),
                release=live.identity,
                content_hash=content_hash(target, live.identity),
                mode="propose",
                candidates=tuple(number for number, _ in candidates),
                snapshot_truncated=snapshot(target, live.policy.snapshot_bytes).truncated,
            )
        else:
            bound = parse_json(ProposalEnvelope, _read(envelope))
        engine = Apply(github, _keys())
        engines["apply"] = engine
        record = engine.run(
            bound, context, _read(input) if input else None, dry_run=dry_run, force_decision=force
        )
        _emit(record, audit)
        if record.status in {"rejected", "failed", "partial", "invalid_state", "mutation_deferred"}:
            raise typer.Exit(1)
    finally:
        github.close()


def _policy(github: GitHub) -> tuple[Policy, str]:
    raw = github.file("triage/policy.yml", github.default_head())
    if raw is None:
        raise BoundaryError("live policy missing")
    return parse_yaml(Policy, raw), digest_bytes(raw)


def _required_labels(policy: Policy) -> tuple[str, ...]:
    mapped = {label for labels in policy.type_labels.values() for label in labels}
    return tuple(
        sorted(
            mapped
            | set(policy.label_allowlist)
            | CONTROL_LABELS
            | {"triage-health", "triage-alert"}
        )
    )


@app.command("check")
@_safe
def check_command(repo: Annotated[str, typer.Option(envvar="GITHUB_REPOSITORY")]) -> None:
    github = _client(repo)
    try:
        policy, _ = _policy(github)
        existing = {label.casefold() for label in github.labels()}
        missing = [label for label in _required_labels(policy) if label.casefold() not in existing]
        typer.echo(canonical_json({"missing_labels": missing, "ok": not missing}).decode())
        if missing:
            raise typer.Exit(1)
    finally:
        github.close()


@app.command("setup-labels")
@_safe
def setup_labels_command(
    repo: Annotated[str, typer.Option(envvar="GITHUB_REPOSITORY")],
    dry_run: Annotated[bool, typer.Option("--dry-run/--write")] = True,
) -> None:
    initial_digest: str | None = None
    initial_release: Release | None = None
    reader = _client(repo)

    def guard(operation: str, issue: int | None) -> None:
        if dry_run or operation != "create_label" or issue is not None:
            raise BoundaryError("label setup write not authorized")
        live = load_live(reader)
        if live is None or live.identity != initial_release:
            raise BoundaryError("label setup blocked by live control or policy change")

    writer = _client(repo, guard)
    try:
        policy, initial_digest = _policy(reader)
        existing = {label.casefold() for label in reader.labels()}
        missing = [label for label in _required_labels(policy) if label.casefold() not in existing]
        if not dry_run:
            baseline = load_live(reader)
            if baseline is None or baseline.identity.policy_digest != initial_digest:
                raise BoundaryError("label setup blocked by live control or policy change")
            initial_release = baseline.identity
            for label in missing:
                writer.create_label(label)
        typer.echo(canonical_json({"dry_run": dry_run, "labels": missing}).decode())
    finally:
        reader.close()
        writer.close()


@app.command("repair")
@_safe
def repair_command(
    repo: Annotated[str, typer.Option(envvar="GITHUB_REPOSITORY")],
    issue: Annotated[
        list[int] | None, typer.Option(min=1, help="Optional issue selection.")
    ] = None,
    limit: Annotated[int, typer.Option(min=1, max=500)] = 50,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Inspection only; never edits state.")
    ] = True,
) -> None:
    if not dry_run or (issue is not None and len(issue) > limit):
        raise BoundaryError("repair requires dry-run and a bounded issue selection")
    github = _client(repo)
    try:
        keys = _keys()
        results = []
        numbers = issue if issue is not None else list(github.issue_numbers(limit + 1))
        for number in numbers[:limit]:
            target = github.issue(number)
            found = discover_state(github.comments(number), target, keys)
            results.append(
                {
                    "issue_number": number,
                    "unreadable": found.unreadable,
                    "state": found.state.state if found.state else None,
                }
            )
        typer.echo(
            canonical_json(
                {"dry_run": True, "issues": results, "truncated": len(numbers) > limit}
            ).decode()
        )
    finally:
        github.close()


if __name__ == "__main__":
    app()
