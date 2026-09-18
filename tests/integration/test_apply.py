import secrets

import pytest

from issue_triage_bot.apply import Apply
from issue_triage_bot.codec import canonical_json
from issue_triage_bot.comment import KeyRing, discover_state
from issue_triage_bot.models import Comment, Issue
from tests.fakes import Repo, prepare


@pytest.fixture
def setup():
    repo = Repo()
    keys = KeyRing("test", secrets.token_bytes(32))
    engine = Apply(repo, keys, reserve_mutation=lambda *_: True)
    return repo, keys, engine


def test_comment_first_replay_and_changed_decision_preserve_human(setup, decision):
    repo, keys, engine = setup
    env, context = prepare(repo)
    result = engine.run(env, context, decision.model_dump_json().encode())
    assert result.status == "applied"
    assert repo.writes == ["create_comment", "add_label", "edit_comment"]
    assert repo.current.labels == ("bug", "human")
    assert discover_state(repo.comments(12), repo.current, keys).state.state == "final"
    before = list(repo.writes)
    assert engine.run(env, context, None).status == "skip"
    assert repo.writes == before
    env, context = prepare(repo, run=101)
    new = canonical_json(decision.model_dump(mode="json") | {"kind": "feature"})
    assert engine.run(env, context, new, force_decision=True).status == "applied"
    assert repo.current.labels == ("enhancement", "human")
    assert len(repo.comment_rows) == 1


@pytest.mark.parametrize("boundary", [1, 2, 3])
def test_resume_after_each_initial_write_even_lost_create_response(setup, decision, boundary):
    repo, keys, engine = setup
    env, context = prepare(repo)
    repo.fail_after = boundary
    result = engine.run(env, context, decision.model_dump_json().encode())
    assert result.status == "partial"
    repo.fail_after = None
    result = engine.run(env, context, None)
    assert result.status in {"applied", "skip"}
    assert len(repo.comment_rows) == 1 and repo.current.labels == ("bug", "human")
    assert discover_state(repo.comments(12), repo.current, keys).state.state == "final"


@pytest.mark.parametrize("boundary", [1, 2, 3, 4])
def test_resume_every_edit_reconciliation_boundary(setup, decision, boundary):
    repo, keys, engine = setup
    env, context = prepare(repo)
    engine.run(env, context, decision.model_dump_json().encode())
    repo.current = Issue(**(repo.current.model_dump() | {"title": "New feature"}))
    env, context = prepare(repo, run=101)
    proposal = canonical_json(decision.model_dump(mode="json") | {"kind": "feature"})
    repo.fail_after = len(repo.writes) + boundary
    assert engine.run(env, context, proposal).status == "partial"
    repo.fail_after = None
    assert engine.run(env, context, None).status in {"applied", "skip"}
    assert repo.current.labels == ("enhancement", "human") and len(repo.comment_rows) == 1
    assert discover_state(repo.comments(12), repo.current, keys).state.state == "final"


@pytest.mark.parametrize("change", ["disable", "policy", "prompt", "generation", "tail_edit"])
def test_fence_rechecked_after_pending_before_labels(setup, decision, change):
    repo, keys, engine = setup
    env, context = prepare(repo)

    def hook(repo, name):
        if change == "disable":
            repo.files[".github/triage-control.yml"] = b"enabled: false\npolicy_generation: 1"
        elif change in {"policy", "prompt"}:
            path = "triage/policy.yml" if change == "policy" else "triage/PROMPT.md"
            repo.files[path] += b"\n# changed"
        elif change == "generation":
            repo.files[".github/triage-control.yml"] = repo.files[
                ".github/triage-control.yml"
            ].replace(b"policy_generation: 1", b"policy_generation: 2")
        else:
            repo.current = Issue(**(repo.current.model_dump() | {"body": "x" * 100000 + "edited"}))

    repo.after_write = hook
    assert engine.run(env, context, decision.model_dump_json().encode()).status == "partial"
    assert repo.writes == ["create_comment"] and repo.current.labels == ("human",)
    assert discover_state(repo.comments(12), repo.current, keys).state.state == "pending"


@pytest.mark.parametrize("rollout", ["dry_run", "shadow"])
def test_nonwriting_rollout_never_mutates(setup, decision, rollout):
    repo, keys, engine = setup
    repo.files["triage/policy.yml"] = repo.files["triage/policy.yml"].replace(
        b"rollout: type_labels", b"rollout: " + rollout.encode()
    )
    env, context = prepare(repo)
    assert engine.run(env, context, decision.model_dump_json().encode()).status == rollout
    assert repo.writes == []


def test_explicit_dry_run_overrides_enabled_type_mode(setup, decision):
    repo, keys, engine = setup
    env, context = prepare(repo)
    assert (
        engine.run(env, context, decision.model_dump_json().encode(), dry_run=True).status
        == "dry_run"
    )
    assert repo.writes == []


def test_security_wins_over_exhausted_inference_budget(setup):
    repo, keys, engine = setup
    repo.current = Issue(**(repo.current.model_dump() | {"body": "Exploit at tail"}))
    env, context = prepare(repo, mode="deferred")
    assert engine.run(env, context, None).status == "review_sensitive"
    assert repo.current.labels == ("human", "needs-triage-review")


def test_three_transient_inference_attempts_then_review(setup):
    repo, keys, engine = setup
    for i in range(3):
        env, context = prepare(repo, run=100 + i)
        result = engine.run(env, context, b"not json")
        assert result.status == ("review_transient" if i == 2 else "transient")
    assert repo.current.labels == ("human", "needs-triage-review")
    state = discover_state(repo.comments(12), repo.current, keys).state
    assert state.attempts == 3 and not state.retry_eligible


def test_human_override_during_pending_is_preserved(setup, decision):
    repo, keys, engine = setup
    env, context = prepare(repo)
    engine.run(env, context, decision.model_dump_json().encode())
    repo.current = Issue(**(repo.current.model_dump() | {"title": "Feature"}))
    env, context = prepare(repo, run=101)

    def hook(repo, name):
        if name == "edit_comment":
            repo.label("bug", "unlabeled", actor="human", kind="User")
            repo.label("bug", "labeled", actor="human", kind="User")

    repo.after_write = hook
    new = canonical_json(decision.model_dump(mode="json") | {"kind": "feature"})
    assert engine.run(env, context, new).status == "applied"
    assert repo.current.labels == ("bug", "enhancement", "human")
    assert "bug" not in discover_state(repo.comments(12), repo.current, keys).state.managed_labels


def test_untrusted_marker_ignored_and_forged_bot_state_blocks(setup, decision):
    repo, keys, engine = setup
    repo.comment_rows = [
        Comment(
            id=99, author_login="attacker", author_type="User", body="<!-- issue-triage:v1 e30= -->"
        )
    ]
    env, context = prepare(repo)
    assert engine.run(env, context, decision.model_dump_json().encode()).status == "applied"
    repo.comment_rows.append(
        Comment(
            id=100,
            author_login="github-actions[bot]",
            author_type="Bot",
            body="<!-- issue-triage:v1 e30= -->",
        )
    )
    env, context = prepare(repo, run=101)
    before = len(repo.writes)
    assert engine.run(env, context, None).status == "invalid_state"
    assert len(repo.writes) == before


def test_unapproved_related_candidate_routes_to_review(setup, decision):
    repo, keys, engine = setup
    env, context = prepare(repo)
    raw = canonical_json(
        decision.model_dump(mode="json")
        | {"related_issues": [{"number": 999, "reason": "invented"}]}
    )
    assert engine.run(env, context, raw).status == "transient"
    assert "bug" not in repo.current.labels and "needs-triage-review" in repo.current.labels


def test_canary_reservation_denial_leaves_signed_pending(setup, decision):
    repo, keys, _ = setup
    engine = Apply(repo, keys, reserve_mutation=lambda *_: False)
    env, context = prepare(repo)
    assert (
        engine.run(env, context, decision.model_dump_json().encode()).status == "mutation_deferred"
    )
    assert repo.writes == ["create_comment"] and repo.current.labels == ("human",)
    assert discover_state(repo.comments(12), repo.current, keys).state.state == "pending"


def test_kill_switch_rechecked_after_reservation(setup, decision):
    repo, keys, _ = setup

    def reserve(*_):
        repo.files[".github/triage-control.yml"] = b"enabled: false\npolicy_generation: 1"
        return True

    engine = Apply(repo, keys, reserve_mutation=reserve)
    env, context = prepare(repo)
    assert engine.run(env, context, decision.model_dump_json().encode()).status == "partial"
    assert repo.writes == ["create_comment"]


def test_audit_contains_no_issue_body_or_rationale(setup, decision):
    repo, keys, engine = setup
    repo.current = Issue(**(repo.current.model_dump() | {"body": "private body canary"}))
    env, context = prepare(repo)
    record = engine.run(env, context, decision.model_dump_json().encode())
    audit = record.model_dump_json()
    assert "private body canary" not in audit and decision.rationale not in audit
    assert record.envelope == env and record.decision_hash is not None


def test_human_override_while_reserving_cannot_be_removed(setup, decision):
    repo, keys, engine = setup
    env, context = prepare(repo)
    engine.run(env, context, decision.model_dump_json().encode())
    repo.current = Issue(**(repo.current.model_dump() | {"title": "Feature"}))
    env, context = prepare(repo, run=101)

    def reserve(envelope, operation, label, limit):
        if operation == "remove_label":
            repo.label("bug", "unlabeled", actor="human", kind="User")
            repo.label("bug", "labeled", actor="human", kind="User")
        return True

    engine = Apply(repo, keys, reserve_mutation=reserve)
    new = canonical_json(decision.model_dump(mode="json") | {"kind": "feature"})
    assert engine.run(env, context, new).status == "applied"
    assert repo.current.labels == ("bug", "enhancement", "human")
    assert "remove_label" not in repo.writes


def test_final_hash_shortcut_survives_new_run_model_failure(setup, decision):
    repo, keys, engine = setup
    env, context = prepare(repo)
    engine.run(env, context, decision.model_dump_json().encode())
    count = len(repo.writes)
    env, context = prepare(repo, run=101)
    assert engine.run(env, context, None).status == "skip"
    assert len(repo.writes) == count and repo.current.labels == ("bug", "human")


@pytest.mark.parametrize("updates", [{"priority": "P0"}, {"kind": "security"}])
def test_sensitive_model_outcome_wins_over_bad_related_reference(setup, decision, updates):
    repo, keys, engine = setup
    env, context = prepare(repo)
    raw = canonical_json(
        decision.model_dump(mode="json")
        | updates
        | {"related_issues": [{"number": 999, "reason": "not a candidate"}]}
    )
    result = engine.run(env, context, raw)
    assert result.status == "review_sensitive"
    state = discover_state(repo.comments(12), repo.current, keys).state
    assert not state.retry_eligible and state.decision is None
    assert repo.current.labels == ("human", "needs-triage-review")


def test_edit_abandons_old_pending_and_reconciles_introduced_labels(setup, decision):
    repo, keys, engine = setup
    env, context = prepare(repo)
    repo.fail_after = 2
    assert engine.run(env, context, decision.model_dump_json().encode()).status == "partial"
    assert "bug" in repo.current.labels
    repo.fail_after = None
    repo.current = Issue(**(repo.current.model_dump() | {"title": "Feature after interruption"}))
    env, context = prepare(repo, run=101)
    raw = canonical_json(decision.model_dump(mode="json") | {"kind": "feature"})
    assert engine.run(env, context, raw).status == "applied"
    assert repo.current.labels == ("enhancement", "human") and len(repo.comment_rows) == 1


def test_kill_switch_before_finalization_keeps_pending_state(setup, decision):
    repo, keys, engine = setup
    env, context = prepare(repo)

    def hook(repo, name):
        if name == "add_label":
            repo.files[".github/triage-control.yml"] = b"enabled: false\npolicy_generation: 1"

    repo.after_write = hook
    result = engine.run(env, context, decision.model_dump_json().encode())
    assert result.status == "partial" and result.state_phase == "pending"
    assert result.after_labels is None
    assert repo.writes == ["create_comment", "add_label"]
    assert discover_state(repo.comments(12), repo.current, keys).state.state == "pending"


def test_related_reference_is_verified_and_reason_sanitized(setup, decision):
    repo, keys, engine = setup
    env, context = prepare(repo)
    raw = canonical_json(
        decision.model_dump(mode="json")
        | {"related_issues": [{"number": 8, "reason": "@admin #99 [evil](https://evil.test)"}]}
    )
    assert engine.run(env, context, raw).status == "applied"
    visible = repo.comment_rows[0].body.split("<!--")[0]
    assert "[Issue 8](https://github.com/example/repo/issues/8)" in visible
    assert "@admin" not in visible and "#99" not in visible and "evil.test" not in visible


def test_retry_exhaustion_cannot_be_reopened_by_deferred_run(setup):
    repo, keys, engine = setup
    for run in range(100, 103):
        env, context = prepare(repo, run=run)
        engine.run(env, context, None)
    writes = len(repo.writes)
    env, context = prepare(repo, run=103, mode="deferred")
    assert engine.run(env, context, None).status == "skip"
    assert len(repo.writes) == writes
    assert not discover_state(repo.comments(12), repo.current, keys).state.retry_eligible


@pytest.mark.parametrize("mode", ["propose", "review_only", "deferred", "resume"])
def test_disabled_control_prevents_every_mode(setup, decision, mode):
    repo, keys, engine = setup
    env, context = prepare(repo, mode=mode)
    repo.files[".github/triage-control.yml"] = b"enabled: false\npolicy_generation: 1"
    assert engine.run(env, context, decision.model_dump_json().encode()).status == "disabled"
    assert repo.writes == []


def test_old_proposal_rejected_before_first_write(setup, decision):
    repo, keys, engine = setup
    env, context = prepare(repo)
    repo.current = Issue(**(repo.current.model_dump() | {"body": "x" * 100000 + "new tail"}))
    result = engine.run(env, context, decision.model_dump_json().encode())
    assert result.status == "rejected" and result.envelope is None
    assert repo.writes == []


def test_outside_canary_gets_only_comment(setup, decision):
    repo, keys, engine = setup
    repo.files[".github/triage-control.yml"] = repo.files[".github/triage-control.yml"].replace(
        b"first_issue: 12", b"first_issue: 13"
    )
    env, context = prepare(repo)
    assert engine.run(env, context, decision.model_dump_json().encode()).status == "applied"
    assert repo.writes == ["create_comment", "edit_comment"] and repo.current.labels == ("human",)


def test_review_only_mode_overrides_pending_classification(setup, decision):
    repo, keys, engine = setup
    env, context = prepare(repo)
    repo.fail_after = 1
    engine.run(env, context, decision.model_dump_json().encode())
    repo.fail_after = None
    env, context = prepare(repo, run=101, mode="review_only")
    assert engine.run(env, context, None).status == "review_sensitive"
    assert repo.current.labels == ("human", "needs-triage-review")
