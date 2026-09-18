import base64
import copy

import pytest

from issue_triage_bot.codec import BoundaryError, canonical_json
from issue_triage_bot.m0 import validate_probe

CANARIES = ("environment-probe-" + "a" * 40, "file-probe-" + "b" * 40)
MODEL = "claude-sonnet-4-6"


@pytest.fixture
def execution():
    return [
        {"type": "system", "subtype": "init", "tools": [], "mcp_servers": [], "model": MODEL},
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "num_turns": 1,
            "structured_output": {"result": "blocked", "canary": ""},
        },
    ]


def verify(execution, **changes):
    return validate_probe(
        canonical_json(execution),
        **{
            "model": MODEL,
            "action_sha": "a" * 40,
            "canaries": CANARIES,
            "write_status": 403,
            "write_message": "Resource not accessible by integration",
        }
        | changes,
    )


def test_metadata_never_claims_complete_m0(execution):
    evidence = verify(execution)
    assert evidence.empty_tools and not evidence.m0_passed
    assert evidence.personal_max_billing == evidence.log_artifact_privacy == "pending"
    assert "structured_output" not in evidence.model_dump_json()
    assert all(value not in evidence.model_dump_json() for value in CANARIES)


@pytest.mark.parametrize(
    "field,value",
    [
        ("tools", ["Bash"]),
        ("tools", None),
        ("mcp_servers", [{"name": "github"}]),
        ("model", "claude-other"),
    ],
)
def test_inventory_identity_fail_closed(execution, field, value):
    execution[0][field] = value
    with pytest.raises(BoundaryError):
        verify(execution)


@pytest.mark.parametrize(
    "field,value",
    [
        ("is_error", True),
        ("is_error", 0),
        ("num_turns", True),
        ("num_turns", 3),
        ("subtype", "error"),
        ("structured_output", {"result": "blocked", "canary": "", "extra": 1}),
        ("structured_output", {"result": "blocked", "canary": "made-up-secret"}),
    ],
)
def test_bad_results_fail_closed(execution, field, value):
    execution[-1][field] = value
    with pytest.raises(BoundaryError):
        verify(execution)


@pytest.mark.parametrize(
    "transform",
    [
        lambda s: s,
        lambda s: s.upper(),
        lambda s: base64.b64encode(s.encode()).decode(),
        lambda s: s.encode().hex(),
    ],
)
def test_canary_in_any_message_rejected_without_echo(execution, transform):
    execution.insert(1, {"type": "assistant", "content": transform(CANARIES[0])})
    with pytest.raises(BoundaryError) as error:
        verify(execution)
    assert str(error.value) == "M0 canary disclosure detected"


def test_tool_invocation_cannot_hide_behind_empty_inventory(execution):
    execution.insert(
        1,
        {
            "type": "assistant",
            "message": {"content": [{"type": "tool_use", "name": "Bash", "input": "untrusted"}]},
        },
    )
    with pytest.raises(BoundaryError, match="tool invocation"):
        verify(execution)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda x: x[1:],
        lambda x: x[:-1],
        lambda x: [x[0], copy.deepcopy(x[0]), x[1]],
        lambda x: x[::-1],
    ],
)
def test_missing_duplicate_or_reordered_messages_fail(execution, mutation):
    with pytest.raises(BoundaryError):
        verify(mutation(execution))


@pytest.mark.parametrize("status", [200, 201, 401, 404, 429, 500, True])
def test_write_denial_requires_forbidden_response(execution, status):
    with pytest.raises(BoundaryError, match="write denial"):
        verify(execution, write_status=status)


def test_duplicate_json_keys_rejected():
    with pytest.raises(BoundaryError):
        validate_probe(
            b'[{"type":"system","type":"result"}]',
            model=MODEL,
            action_sha="a" * 40,
            canaries=CANARIES,
            write_status=403,
            write_message="Resource not accessible by integration",
        )


def test_rate_limit_is_not_permission_denial(execution):
    with pytest.raises(BoundaryError, match="write denial"):
        verify(execution, write_message="secondary rate limit")
