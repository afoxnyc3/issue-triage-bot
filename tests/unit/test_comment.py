import base64
import json
import secrets

import pytest

from issue_triage_bot.codec import BoundaryError, canonical_json, decision_hash
from issue_triage_bot.comment import (
    KeyRing,
    discover_state,
    read_state,
    render_comment,
    state_marker,
)
from issue_triage_bot.models import Comment, CommentState
from issue_triage_bot.sanitize import sanitize


@pytest.fixture
def keys():
    return KeyRing("current", secrets.token_bytes(32))


@pytest.fixture
def state(envelope, decision):
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
        intended_labels=("bug",),
    )


def bot_comment(body, **updates):
    return Comment(
        id=15, author_login="github-actions[bot]", author_type="Bot", body=body, **updates
    )


def tamper(marker, mutate):
    data = json.loads(base64.b64decode(marker.split()[2]))
    mutate(data)
    return "<!-- issue-triage:v1 " + base64.b64encode(canonical_json(data)).decode() + " -->"


def test_roundtrip_and_visible_payload(state, keys, issue):
    body = render_comment(state, keys)
    assert read_state(bot_comment(body), issue, keys) == state
    assert "Priority (advisory): P2" in body
    assert discover_state([bot_comment(body)], issue, keys).comment_id == 15


@pytest.mark.parametrize(
    "target,value",
    [("outcome", "review_sensitive"), ("attempts", 2), ("intended_labels", ["critical"])],
)
def test_forged_payload_rejected(state, keys, issue, target, value):
    forged = tamper(state_marker(state, keys), lambda d: d["payload"].__setitem__(target, value))
    with pytest.raises(BoundaryError):
        read_state(bot_comment(forged), issue, keys)
    assert discover_state([bot_comment(forged)], issue, keys).unreadable


def test_signature_and_key_id_tampering(state, keys, issue):
    marker = state_marker(state, keys)
    for field, value in [("signature", "0" * 64), ("key_id", "unknown")]:
        forged = tamper(marker, lambda d, field=field, value=value: d.__setitem__(field, value))
        with pytest.raises(BoundaryError):
            read_state(bot_comment(forged), issue, keys)


def test_current_previous_rotation_and_retirement(state, issue):
    old = secrets.token_bytes(32)
    new = secrets.token_bytes(32)
    old_marker = state_marker(state, KeyRing("old", old))
    rotated = KeyRing("new", new, previous_id="old", previous_key=old)
    assert read_state(bot_comment(old_marker), issue, rotated) == state
    assert read_state(bot_comment(state_marker(state, rotated)), issue, rotated) == state
    with pytest.raises(BoundaryError):
        read_state(bot_comment(old_marker), issue, KeyRing("new", new))
    assert old.hex() not in repr(rotated) and new.hex() not in repr(rotated)


@pytest.mark.parametrize(
    "login,kind", [("attacker", "User"), ("github-actions[bot]", "User"), ("other[bot]", "Bot")]
)
def test_foreign_authors_ignored_even_with_copied_valid_signature(state, keys, issue, login, kind):
    comment = Comment(id=25, author_login=login, author_type=kind, body=state_marker(state, keys))
    assert discover_state([comment], issue, keys).state is None
    assert not discover_state([comment], issue, keys).unreadable
    with pytest.raises(BoundaryError, match="author"):
        read_state(comment, issue, keys)


def test_duplicate_and_unknown_markers_fail_closed(state, keys, issue):
    marker = state_marker(state, keys)
    assert discover_state([bot_comment(marker), bot_comment(marker)], issue, keys).unreadable
    for body in [
        marker + "\n" + marker,
        marker + " trailing",
        "<!-- issue-triage:v99 abc -->",
        "<!-- issue-triage:v1 not-base64 -->",
        "<!-- issue-triage:v1 e30= -->",
    ]:
        assert discover_state([bot_comment(body)], issue, keys).unreadable


def test_cross_issue_copied_state_rejected(state, keys, issue):
    other = type(issue)(**(issue.model_dump() | {"number": 99}))
    with pytest.raises(BoundaryError, match="identity"):
        read_state(bot_comment(state_marker(state, keys)), other, keys)


def test_wrong_decision_hash_never_signed(state, keys):
    broken = CommentState(**(state.model_dump() | {"decision_hash": "0" * 64}))
    with pytest.raises(BoundaryError, match="decision hash"):
        state_marker(broken, keys)


@pytest.mark.parametrize(
    "text",
    [
        '<a href="https://evil.test">@team #123</a>',
        "&lt;img src=x onerror=x&gt;hello",
        "![secret](https://evil.test/a) [look](https://evil.test)",
        "[nested [title]](https://evil.test/(nested))",
        "[click][reference]\n[reference]: https://evil.test",
        "`@org/team` **#25** owner/repo#27",
        "https://evil.test/a www.evil.test mailto:test@example.test",
        "&amp;#64;admin &amp;#35;55",
        "\u202e@admin\x00#1",
    ],
)
def test_rendered_text_never_active_markup(text):
    value = sanitize(text)
    assert not any(c in value for c in "@#<>[]`*_&\\")
    assert "https://" not in value and "www." not in value
    assert "\u202e" not in value and "\x00" not in value
    assert len(value) <= 600


def test_sanitizer_bounds_and_multilingual():
    assert len(sanitize("x" * 1000, limit=120)) == 120
    assert sanitize("错误を報告します") == "错误を報告します"
    assert sanitize("[read](https://example.test)") == "read"
    assert sanitize("![picture](https://example.test)") == ""


@pytest.mark.parametrize(
    "change",
    [
        {"state_version": True},
        {"state_version": 0},
        {"state": "final"},
        {"written_at": "2026-99-18T12:00:00Z"},
        {"written_at": "2026-09-18T12:00:00+00:00"},
        {"outcome": "transient"},
        {"outcome": "review_transient"},
        {"attempts": 4},
        {"retry_eligible": True},
        {"decision": None},
        {"intended_labels": ["bug", "bug"]},
        {"unknown": "field"},
    ],
)
def test_invalid_state_schema_rejected(state, change):
    from issue_triage_bot.codec import parse_json

    with pytest.raises(BoundaryError):
        parse_json(CommentState, canonical_json(state.model_dump(mode="json") | change))


def test_discovery_scans_every_comment(state, keys, issue):
    comments = [
        Comment(id=i + 1, author_login="human", author_type="User", body="noise")
        for i in range(105)
    ]
    comments.append(bot_comment(state_marker(state, keys)))
    assert discover_state(iter(comments), issue, keys).state == state


def test_oversized_comment_is_unreadable(state, keys, issue):
    body = "x" * (48 * 1024) + state_marker(state, keys)
    assert discover_state([bot_comment(body)], issue, keys).unreadable


def test_invalid_key_configuration_is_redacted():
    key = secrets.token_bytes(32)
    for args in [
        dict(current_id="bad id", current_key=key),
        dict(current_id="one", current_key=b"short"),
        dict(current_id="one", current_key=key, previous_id="old"),
        dict(current_id="one", current_key=key, previous_id="one", previous_key=key),
    ]:
        with pytest.raises(BoundaryError) as error:
            KeyRing(**args)
        assert key.hex() not in str(error.value)
        assert repr(key) not in str(error.value)
