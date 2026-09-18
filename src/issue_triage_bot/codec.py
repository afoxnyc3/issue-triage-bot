"""Bounded JSON parsing and canonical hashing without logging untrusted inputs."""

import hashlib
import json
from typing import TypeVar

from pydantic import ValidationError

from .models import Issue, ProposalEnvelope, Release, RunContext, StrictModel, TriageDecision

MAX_PROPOSAL_BYTES = 16 * 1024
Model = TypeVar("Model", bound=StrictModel)


class BoundaryError(ValueError):
    """A redacted error suitable for audit records; never includes input content."""


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise BoundaryError("duplicate JSON field")
        result[key] = value
    return result


def _reject_constant(value: str) -> object:
    raise BoundaryError("nonfinite JSON number")


def parse_json(model: type[Model], raw: bytes, *, max_bytes: int = MAX_PROPOSAL_BYTES) -> Model:
    if len(raw) > max_bytes:
        raise BoundaryError("input exceeds size limit")
    try:
        parsed = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_reject_constant
        )
        # JSON mode allows JSON enum strings/arrays, but never numeric/bool coercion.
        return model.model_validate_json(canonical_json(parsed), strict=True)
    except (ValueError, ValidationError, RecursionError, UnicodeError):
        raise BoundaryError("invalid structured input") from None


def content_hash(issue: Issue, release: Release) -> str:
    return digest_bytes(
        canonical_json(
            {
                "repository": issue.repository,
                "number": issue.number,
                "node_id": issue.node_id,
                "title": issue.title,
                "body": issue.body,
                "release": release.model_dump(mode="json"),
            }
        )
    )


def decision_hash(decision: TriageDecision, envelope: ProposalEnvelope) -> str:
    return digest_bytes(
        canonical_json(
            {
                "decision": decision.model_dump(mode="json"),
                "envelope": envelope.model_dump(mode="json"),
            }
        )
    )


def validate_envelope(
    envelope: ProposalEnvelope, context: RunContext, issue: Issue, release: Release
) -> None:
    """Context/release must originate from trusted workflow and fresh GitHub reads."""
    for name in RunContext.model_fields:
        if getattr(envelope, name) != getattr(context, name):
            raise BoundaryError("workflow identity mismatch")
    if (issue.repository, issue.number, issue.node_id) != (
        context.repository,
        context.issue_number,
        context.node_id,
    ):
        raise BoundaryError("issue identity mismatch")
    if envelope.release != release:
        raise BoundaryError("release mismatch")
    if envelope.content_hash != content_hash(issue, release):
        raise BoundaryError("stale content")
