import pytest

from issue_triage_bot.codec import content_hash
from issue_triage_bot.models import Issue, ProposalEnvelope, Release, RunContext, TriageDecision


@pytest.fixture
def release():
    return Release(
        provider="anthropic",
        model="claude-sonnet-fixture-exact",
        action_sha="a" * 40,
        schema_version=1,
        inference_digest="b" * 64,
        prompt_digest="c" * 64,
        policy_digest="d" * 64,
        control_digest="e" * 64,
        policy_generation=1,
    )


@pytest.fixture
def issue():
    return Issue(
        repository="example/repo", number=12, node_id="I_fixture", title="Crash", body=None
    )


@pytest.fixture
def context(issue):
    return RunContext(
        repository=issue.repository,
        issue_number=issue.number,
        node_id=issue.node_id,
        run_id=100,
        run_attempt=1,
    )


@pytest.fixture
def envelope(context, issue, release):
    return ProposalEnvelope(
        **context.model_dump(),
        release=release,
        content_hash=content_hash(issue, release),
        mode="propose",
        candidates=(8,),
    )


@pytest.fixture
def decision():
    return TriageDecision.model_validate_json("""{"schema_version":1,"kind":"bug","priority":"P2",
    "complexity":"simple","rationale":"Reproducible crash"}""")
