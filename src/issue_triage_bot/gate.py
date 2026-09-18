"""Deterministic full-content security scanning and bounded UTF-8 snapshots."""

import unicodedata
from dataclasses import dataclass

from .models import Issue


def security_hit(issue: Issue, terms: tuple[str, ...]) -> bool:
    text = unicodedata.normalize("NFKC", issue.title + "\n" + (issue.body or "")).casefold()
    # Conservative substring matching adds review only, never type classification.
    return any(unicodedata.normalize("NFKC", term).casefold() in text for term in terms)


@dataclass(frozen=True)
class Snapshot:
    title: str
    body: str
    truncated: bool


def snapshot(issue: Issue, max_bytes: int) -> Snapshot:
    if max_bytes < 0:
        raise ValueError("snapshot budget must be nonnegative")
    title_bytes = issue.title.encode("utf-8")
    body_bytes = (issue.body or "").encode("utf-8")
    title = title_bytes[:max_bytes].decode("utf-8", errors="ignore")
    remaining = max_bytes - len(title.encode("utf-8"))
    body = body_bytes[:remaining].decode("utf-8", errors="ignore")
    return Snapshot(title, body, len(title_bytes) + len(body_bytes) > max_bytes)
