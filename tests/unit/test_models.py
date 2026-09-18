import json

import pytest
from pydantic import ValidationError

from issue_triage_bot.codec import (
    BoundaryError,
    canonical_json,
    content_hash,
    decision_hash,
    parse_json,
    validate_envelope,
)
from issue_triage_bot.models import IssueKind, ProposalEnvelope, Release, TriageDecision


def changed(instance, **values):
    # Validate updates, rather than using model_copy(update=...) which skips validation.
    return type(instance).model_validate_json(json.dumps(instance.model_dump(mode="json") | values))


def test_valid_json_immutable_and_exported_schema(decision):
    assert decision.kind is IssueKind.BUG
    assert decision.related_issues == ()
    with pytest.raises(ValidationError):
        decision.priority = "P1"
    schema = TriageDecision.model_json_schema()
    assert schema["additionalProperties"] is False
    assert schema["$defs"]["RelatedIssue"]["additionalProperties"] is False
    assert parse_json(TriageDecision, decision.model_dump_json().encode()) == decision


@pytest.mark.parametrize(
    "update",
    [
        {"labels": ["critical"]},
        {"assignee": "attacker"},
        {"kind": "arbitrary"},
        {"priority": "urgent"},
        {"schema_version": True},
        {"schema_version": 1.0},
        {"schema_version": "1"},
        {"rationale": "x" * 601},
        {"area": "x" * 41},
        {"missing_information": ["x"] * 6},
        {"missing_information": ["x" * 121]},
        {"related_issues": [{"number": True, "reason": "x"}]},
        {"related_issues": [{"number": "8", "reason": "x"}]},
        {"related_issues": [{"number": 8, "reason": "x", "url": "bad"}]},
        {"related_issues": [{"number": 8, "reason": "x"}] * 2},
        {"rationale": "\ud800"},
    ],
)
def test_untrusted_decision_rejected_and_redacted(decision, update):
    raw = canonical_json(decision.model_dump(mode="json") | update)
    with pytest.raises(BoundaryError) as error:
        parse_json(TriageDecision, raw)
    assert str(error.value) == "invalid structured input"


@pytest.mark.parametrize(
    "raw",
    [
        b'{"kind":"bug","kind":"security"}',
        b'{"x":NaN}',
        b'{"x":Infinity}',
        b"null",
        b"[]",
        b"\xff",
        b'"' + b"x" * 16384 + b'"',
        b"[" * 2000,
    ],
)
def test_invalid_json_boundary(raw):
    with pytest.raises(BoundaryError):
        parse_json(TriageDecision, raw)


def test_full_content_hash_and_ignored_label_metadata(issue, release):
    before = content_hash(issue, release)
    assert content_hash(changed(issue, body="x" * 100000 + "tail"), release) != before
    assert content_hash(changed(issue, labels=["human"]), release) == before
    assert content_hash(changed(issue, title="new"), release) != before
    assert content_hash(changed(issue, body=""), release) != before


@pytest.mark.parametrize(
    "field,value",
    [
        ("model", "claude-fixture-new"),
        ("action_sha", "f" * 40),
        ("inference_digest", "f" * 64),
        ("prompt_digest", "f" * 64),
        ("policy_digest", "f" * 64),
        ("control_digest", "f" * 64),
        ("policy_generation", 2),
    ],
)
def test_every_release_fence_affects_hash_and_validation(
    issue, release, envelope, context, decision, field, value
):
    new_release = changed(release, **{field: value})
    assert content_hash(issue, release) != content_hash(issue, new_release)
    new_envelope = changed(envelope, release=new_release.model_dump(mode="json"))
    assert decision_hash(decision, envelope) != decision_hash(decision, new_envelope)
    with pytest.raises(BoundaryError, match="release mismatch"):
        validate_envelope(envelope, context, issue, new_release)


@pytest.mark.parametrize(
    "field,value",
    [
        ("repository", "other/repo"),
        ("issue_number", 99),
        ("node_id", "I_other"),
        ("run_id", 999),
        ("run_attempt", 2),
    ],
)
def test_cross_run_or_issue_replay_rejected(envelope, context, issue, release, field, value):
    with pytest.raises(BoundaryError, match="workflow identity"):
        validate_envelope(changed(envelope, **{field: value}), context, issue, release)


def test_happy_envelope_and_stale_issue(envelope, context, issue, release):
    validate_envelope(envelope, context, issue, release)
    with pytest.raises(BoundaryError, match="stale content"):
        validate_envelope(envelope, context, changed(issue, body="edited"), release)
    with pytest.raises(BoundaryError, match="issue identity"):
        validate_envelope(envelope, context, changed(issue, node_id="I_other"), release)


@pytest.mark.parametrize(
    "values",
    [{"candidates": [12]}, {"candidates": [8, 8]}, {"candidates": [True]}, {"unexpected": "x"}],
)
def test_envelope_schema_rejects_invalid_candidates(envelope, values):
    with pytest.raises(BoundaryError):
        parse_json(ProposalEnvelope, canonical_json(envelope.model_dump(mode="json") | values))


@pytest.mark.parametrize(
    "values",
    [
        {"provider": "openai"},
        {"model": "sonnet"},
        {"model": "sonnet-latest"},
        {"schema_version": True},
    ],
)
def test_unsupported_provider_or_unpinned_model_fails(release, values):
    with pytest.raises(BoundaryError):
        parse_json(Release, canonical_json(release.model_dump(mode="json") | values))
