from pathlib import Path

import pytest

from issue_triage_bot.codec import BoundaryError, canonical_json, content_hash, decision_hash
from issue_triage_bot.config import Control, Policy, parse_yaml
from issue_triage_bot.gate import security_hit, snapshot
from issue_triage_bot.models import CommentState
from issue_triage_bot.policy import LabelEvent, evaluate, reconcile


@pytest.fixture
def policy():
    return parse_yaml(Policy, Path("triage/policy.yml").read_bytes())


def with_fields(instance, **values):
    return type(instance).model_validate_json(
        canonical_json(instance.model_dump(mode="json") | values)
    )


def event(label, *, actor="github-actions[bot]", kind="Bot", action="labeled", id=1):
    return LabelEvent(id=id, event=action, label=label, actor_login=actor, actor_type=kind)


def owned_state(envelope, decision, labels):
    return CommentState(
        state_version=1,
        state="pending",
        outcome="applied",
        retry_eligible=False,
        attempts=0,
        written_at="2026-09-18T12:00:00Z",
        envelope=envelope,
        decision=decision,
        decision_hash=decision_hash(decision, envelope),
        intended_labels=labels,
        pending_additions=labels,
    )


def test_safe_committed_defaults(policy):
    control = parse_yaml(Control, Path(".github/triage-control.yml").read_bytes())
    assert not control.enabled and policy.rollout == "dry_run"
    assert control.daily_inference_limit == 40


@pytest.mark.parametrize(
    "raw",
    [
        b"enabled: true\nenabled: false\npolicy_generation: 1",
        b"enabled: &x false\ncanary: *x\npolicy_generation: 1",
        b"enabled: !!python/object/apply:os.system [echo]",
        b'enabled: "false"\npolicy_generation: 1',
        b"enabled: false\npolicy_generation: true",
        b"[]",
        b"x" * 65537,
    ],
)
def test_hostile_yaml_rejected(raw):
    with pytest.raises(BoundaryError):
        parse_yaml(Control, raw)


def test_full_tail_scanned_before_snapshot(issue, release, policy):
    long = with_fields(issue, body="benign " * 10000 + "credential leak")
    snap = snapshot(long, 256)
    assert snap.truncated and "credential leak" not in snap.body
    assert security_hit(long, policy.security_terms)
    assert content_hash(long, release) != content_hash(issue, release)
    assert not security_hit(issue, policy.security_terms)
    assert security_hit(with_fields(issue, title="ＳＥＣＵＲＩＴＹ bug"), policy.security_terms)


def test_snapshot_has_shared_utf8_budget(issue):
    multi = with_fields(issue, title="🐛" * 10, body="问题" * 50)
    for limit in range(0, 51):
        snap = snapshot(multi, limit)
        assert len(snap.title.encode()) + len(snap.body.encode()) <= limit
        assert snap.truncated


@pytest.mark.parametrize("update", [{"kind": "security"}, {"priority": "P0"}])
def test_sensitive_model_never_type_labels(policy, decision, update):
    policy = with_fields(policy, rollout="type_labels")
    intent = evaluate(policy, with_fields(decision, **update), sensitive=False, deferred=True)
    assert intent.outcome == "review_sensitive" and intent.labels == ("needs-triage-review",)


def test_gate_wins_over_outage_and_budget(policy):
    assert evaluate(policy, None, sensitive=True, deferred=True).outcome == "review_sensitive"


def test_retry_failure_reaches_review_and_stops_after_three(policy):
    for attempts in range(3):
        intent = evaluate(policy, None, sensitive=False, previous_attempts=attempts)
        assert "needs-triage-review" in intent.labels
        assert intent.attempts == attempts + 1
        assert intent.retry_eligible == (attempts < 2)
    assert intent.outcome == "review_transient"


def test_advisory_priority_and_allowlist(policy, decision):
    for rollout in ["dry_run", "shadow", "comment_only"]:
        assert (
            evaluate(with_fields(policy, rollout=rollout), decision, sensitive=False).labels == ()
        )
    enabled = with_fields(policy, rollout="type_labels")
    assert evaluate(enabled, decision, sensitive=False).labels == ("bug",)
    assert (
        evaluate(with_fields(enabled, label_allowlist=[]), decision, sensitive=False).labels == ()
    )


@pytest.mark.parametrize("label", ["P0", "P1-high", "priority:critical", "PRIORITY-high"])
def test_priority_mapping_rejected(policy, label):
    with pytest.raises(ValueError):
        with_fields(policy, type_labels={"bug": [label]})


def test_removal_needs_signature_policy_and_timeline(policy, envelope, decision):
    state = owned_state(envelope, decision, ("bug", "human", "old"))
    events = (event("bug"), event("human"), event("old"))
    plan = reconcile(
        ("bug", "human", "old"), (), policy=policy, authenticated_state=state, events=events
    )
    assert plan.remove == ("bug",)
    retired = with_fields(policy, retired_labels=["old"])
    assert reconcile(
        ("old",), (), policy=retired, authenticated_state=state, events=events
    ).remove == ("old",)
    assert not reconcile(
        ("bug",), (), policy=policy, authenticated_state=None, events=events
    ).remove
    assert not reconcile(("bug",), (), policy=policy, authenticated_state=state, events=()).remove


def test_human_remove_readd_and_case_override(policy, envelope, decision):
    state = owned_state(envelope, decision, ("bug",))
    events = (
        event("bug"),
        event("BUG", actor="human", kind="User", action="unlabeled", id=2),
        event("Bug", actor="human", kind="User", id=3),
    )
    plan = reconcile(("BUG",), (), policy=policy, authenticated_state=state, events=events)
    assert not plan.remove and plan.human_overrides == ("BUG",)
    plan = reconcile((), ("bug",), policy=policy, authenticated_state=state, events=events[:2])
    assert not plan.add and plan.human_overrides == ("bug",)


def test_pending_resume_and_unowned_labels(policy, envelope, decision):
    state = owned_state(envelope, decision, ("bug",))
    assert reconcile((), ("bug",), policy=policy, authenticated_state=state, events=()).add == (
        "bug",
    )
    plan = reconcile(
        ("bug",), ("bug",), policy=policy, authenticated_state=state, events=(event("bug"),)
    )
    assert not plan.add and plan.managed == ("bug",)
    plan = reconcile(
        ("bug",), ("bug",), policy=policy, authenticated_state=None, events=(event("bug"),)
    )
    assert not plan.managed


def test_unapproved_labels_never_added(policy):
    assert not reconcile(
        (), ("critical", "random"), policy=policy, authenticated_state=None, events=()
    ).add


def test_pending_intent_does_not_claim_preexisting_legacy_label(policy, envelope, decision):
    state = owned_state(envelope, decision, ("bug",))
    state = with_fields(state, pending_additions=[])
    plan = reconcile(("bug",), (), policy=policy, authenticated_state=state, events=(event("bug"),))
    assert not plan.remove
    plan = reconcile(
        ("bug",), ("bug",), policy=policy, authenticated_state=state, events=(event("bug"),)
    )
    assert not plan.managed
