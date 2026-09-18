"""HMAC-authenticated comment state and safe managed-comment rendering."""

import base64
import binascii
import hashlib
import hmac
import re
from collections.abc import Iterable
from dataclasses import dataclass

from .codec import BoundaryError, canonical_json, decision_hash, parse_json
from .models import Comment, CommentState, Issue, SignedState
from .sanitize import sanitize

MARKER = "<!-- issue-triage:"
STATE_PATTERN = re.compile(r"<!-- issue-triage:v1 ([A-Za-z0-9+/=]+) -->")
MAX_STATE_BYTES = 24 * 1024
MAX_COMMENT_BYTES = 48 * 1024
BOT_LOGIN = "github-actions[bot]"


class KeyRing:
    """Keys are deliberately absent from repr and all error messages."""

    def __init__(
        self,
        current_id: str,
        current_key: bytes,
        *,
        previous_id: str | None = None,
        previous_key: bytes | None = None,
    ) -> None:
        pairs = [(current_id, current_key)]
        if (previous_id is None) != (previous_key is None):
            raise BoundaryError("incomplete key rotation configuration")
        if previous_id is not None and previous_key is not None:
            if previous_id == current_id:
                raise BoundaryError("duplicate key identifier")
            pairs.append((previous_id, previous_key))
        for key_id, key in pairs:
            if not re.fullmatch(r"[a-zA-Z0-9_-]{1,40}", key_id) or len(key) < 32:
                raise BoundaryError("invalid state signing configuration")
        self.current_id = current_id
        self._keys = dict(pairs)

    def _signature(self, key_id: str, state: CommentState) -> str:
        key = self._keys.get(key_id)
        if key is None:
            raise BoundaryError("unknown state key identifier")
        message = canonical_json({"key_id": key_id, "payload": state.model_dump(mode="json")})
        return hmac.new(key, message, hashlib.sha256).hexdigest()

    def sign(self, state: CommentState) -> SignedState:
        if state.decision_hash != decision_hash(state.decision, state.envelope):
            raise BoundaryError("state decision hash mismatch")
        return SignedState(
            key_id=self.current_id, payload=state, signature=self._signature(self.current_id, state)
        )

    def verify(self, signed: SignedState) -> CommentState:
        signature = self._signature(signed.key_id, signed.payload)
        if not hmac.compare_digest(signature, signed.signature):
            raise BoundaryError("invalid state signature")
        if signed.payload.decision_hash != decision_hash(
            signed.payload.decision,
            signed.payload.envelope,
        ):
            raise BoundaryError("state decision hash mismatch")
        return signed.payload


def state_marker(state: CommentState, keys: KeyRing) -> str:
    raw = canonical_json(keys.sign(state).model_dump(mode="json"))
    if len(raw) > MAX_STATE_BYTES:
        raise BoundaryError("state exceeds size limit")
    encoded = base64.b64encode(raw).decode("ascii")
    return f"<!-- issue-triage:v1 {encoded} -->"


def read_state(comment: Comment, issue: Issue, keys: KeyRing) -> CommentState:
    if comment.author_login != BOT_LOGIN or comment.author_type != "Bot":
        raise BoundaryError("untrusted comment author")
    if len(comment.body.encode("utf-8")) > MAX_COMMENT_BYTES:
        raise BoundaryError("comment exceeds size limit")
    if comment.body.count(MARKER) != 1:
        raise BoundaryError("ambiguous state marker")
    match = STATE_PATTERN.search(comment.body)
    if match is None or comment.body[match.end() :].strip():
        raise BoundaryError("invalid state marker")
    try:
        raw = base64.b64decode(match.group(1), validate=True)
    except (ValueError, binascii.Error):
        raise BoundaryError("invalid state encoding") from None
    signed = parse_json(SignedState, raw, max_bytes=MAX_STATE_BYTES)
    state = keys.verify(signed)
    env = state.envelope
    if (env.repository, env.issue_number, env.node_id) != (
        issue.repository,
        issue.number,
        issue.node_id,
    ):
        raise BoundaryError("state identity mismatch")
    return state


@dataclass(frozen=True)
class Discovery:
    comment_id: int | None = None
    state: CommentState | None = None
    unreadable: bool = False


def discover_state(comments: Iterable[Comment], issue: Issue, keys: KeyRing) -> Discovery:
    """Caller must paginate all comments; foreign authors never establish ownership."""
    candidates = [
        c
        for c in comments
        if c.author_login == BOT_LOGIN and c.author_type == "Bot" and MARKER in c.body
    ]
    if not candidates:
        return Discovery()
    if len(candidates) != 1:
        return Discovery(unreadable=True)
    comment = candidates[0]
    try:
        return Discovery(comment.id, read_state(comment, issue, keys))
    except BoundaryError:
        return Discovery(unreadable=True)


def render_comment(
    state: CommentState,
    keys: KeyRing,
    *,
    area_name: str | None = None,
    verified_related: tuple[tuple[int, str], ...] = (),
) -> str:
    descriptions = {
        "applied": "Triage proposal validated.",
        "review_sensitive": "This report needs human review. Automatic classification is withheld.",
        "review_transient": "Triage failed after three attempts. Please review.",
        "transient": "Automated triage could not complete. A retry is pending.",
        "deferred": "Triage is deferred until inference budget is available.",
    }
    lines = ["### Issue triage", "", descriptions[state.outcome]]
    if state.decision is not None and state.outcome == "applied":
        decision = state.decision
        lines.extend(
            [
                "",
                f"- Kind: {decision.kind.value}",
                f"- Priority (advisory): {decision.priority}",
                f"- Complexity: {decision.complexity}",
            ]
        )
        if area_name is not None:
            lines.append(f"- Area: {sanitize(area_name, limit=80)}")
        lines.extend(["", f"> {sanitize(decision.rationale)}"])
        if decision.missing_information:
            lines.extend(["", "Requested information:"])
            lines.extend(f"- {sanitize(item, limit=120)}" for item in decision.missing_information)
        if verified_related:
            lines.extend(["", "Possibly related:"])
            for number, reason in verified_related:
                url = f"https://github.com/{state.envelope.repository}/issues/{number}"
                lines.append(f"- [Issue {number}]({url}): {sanitize(reason, limit=120)}")
    lines.extend(["", state_marker(state, keys)])
    body = "\n".join(lines)
    if len(body.encode("utf-8")) > MAX_COMMENT_BYTES:
        raise BoundaryError("rendered comment exceeds size limit")
    return body
