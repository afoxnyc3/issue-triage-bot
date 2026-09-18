"""Narrow GitHub REST client with bounded reads, pagination and guarded writes."""

import base64
import binascii
import re
import time
from collections import Counter
from collections.abc import Callable, Iterator
from datetime import date, timedelta
from typing import cast
from urllib.parse import quote

import httpx

from .codec import BoundaryError, canonical_json, decode_json, parse_json
from .models import Comment, Issue
from .policy import LabelEvent

API = "https://api.github.com"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
WriteGuard = Callable[[str, int | None], None]


class GitHubError(BoundaryError):
    def __init__(self, status: int | None, *, transient: bool, uncertain: bool = False) -> None:
        self.status = status
        self.transient = transient
        self.uncertain = uncertain
        super().__init__("GitHub transport failure" if status is None else f"GitHub HTTP {status}")


def obj(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise BoundaryError("invalid GitHub object")
    return cast(dict[str, object], value)


def text(value: object) -> str:
    if not isinstance(value, str):
        raise BoundaryError("invalid GitHub string")
    return value


def positive_id(value: object) -> int:
    if type(value) is not int or value <= 0:
        raise BoundaryError("invalid GitHub identifier")
    return value


def array(value: object) -> list[object]:
    if not isinstance(value, list):
        raise BoundaryError("invalid GitHub array")
    return value


def _transient(response: httpx.Response) -> bool:
    if response.status_code == 429 or response.status_code >= 500:
        return True
    if response.status_code == 403:
        if (
            response.headers.get("retry-after")
            or response.headers.get("x-ratelimit-remaining") == "0"
        ):
            return True
        # Inspect only for classification, never echo or persist the error body.
        return b"secondary rate limit" in response.content.lower()
    return False


class GitHub:
    def __init__(
        self,
        repository: str,
        token: str,
        *,
        transport: httpx.BaseTransport | None = None,
        write_guard: WriteGuard | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise BoundaryError("invalid repository")
        if any(part in {".", ".."} for part in repository.split("/")):
            raise BoundaryError("invalid repository")
        self.repository = repository
        self._prefix = f"/repos/{repository}"
        self._write_guard = write_guard
        self._sleep = sleep
        self._http = httpx.Client(
            base_url=API,
            timeout=30,
            follow_redirects=False,
            transport=transport,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2026-03-10",
            },
        )

    def close(self) -> None:
        self._http.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str | int] | None = None,
        payload: object = None,
        operation: str = "read",
        issue: int | None = None,
        headers_out: dict[str, str] | None = None,
    ) -> object:
        if not path.startswith(self._prefix + "/") and path not in {self._prefix, "/search/issues"}:
            raise BoundaryError("GitHub request outside repository scope")
        writing = method != "GET"
        attempts = 1 if writing else 3
        for attempt in range(attempts):
            if writing:
                if self._write_guard is None:
                    raise BoundaryError("read-only GitHub client")
                self._write_guard(operation, issue)
            try:
                with self._http.stream(method, path, params=params, json=payload) as response:
                    chunks: list[bytes] = []
                    length = 0
                    for chunk in response.iter_bytes():
                        length += len(chunk)
                        if length > MAX_RESPONSE_BYTES:
                            raise BoundaryError("GitHub response exceeds size limit")
                        chunks.append(chunk)
                    body = b"".join(chunks)
                    # A detached response permits classification without retaining stream handles.
                    received = httpx.Response(
                        response.status_code, headers=response.headers, content=body
                    )
            except httpx.TransportError:
                if attempt + 1 == attempts:
                    raise GitHubError(None, transient=True, uncertain=writing) from None
                self._sleep(float(2**attempt))
                continue
            if 200 <= received.status_code < 300:
                if headers_out is not None:
                    headers_out.update(received.headers)
                if received.status_code == 204:
                    return None
                return decode_json(body, max_bytes=MAX_RESPONSE_BYTES)
            transient = _transient(received)
            if transient and attempt + 1 < attempts:
                delay = 2**attempt
                retry_after = received.headers.get("retry-after")
                if retry_after:
                    try:
                        delay = max(delay, int(retry_after))
                    except ValueError:
                        raise GitHubError(received.status_code, transient=True) from None
                if delay <= 60:
                    self._sleep(float(delay))
                    continue
            raise GitHubError(
                received.status_code,
                transient=transient,
                uncertain=writing and received.status_code >= 500,
            )
        raise AssertionError("unreachable request loop")

    def _pages(self, path: str) -> Iterator[dict[str, object]]:
        # Construct page URLs locally. Never follow attacker-controlled Link hosts.
        for page in range(1, 1001):
            headers: dict[str, str] = {}
            items = array(
                self._request(
                    "GET", path, params={"per_page": 100, "page": page}, headers_out=headers
                )
            )
            next_link = httpx.Response(200, headers=headers).links.get("next", {}).get("url")
            if next_link is not None:
                url = httpx.URL(next_link)
                if (
                    url.scheme != "https"
                    or url.host != "api.github.com"
                    or url.port not in {None, 443}
                    or url.userinfo
                    or url.fragment
                    or url.path != path
                    or url.params.get("page") != str(page + 1)
                    or url.params.get("per_page", "100") != "100"
                    or set(url.params) - {"page", "per_page"}
                ):
                    raise BoundaryError("invalid GitHub pagination link")
            if len(items) > 100:
                raise BoundaryError("invalid GitHub page size")
            for item in items:
                yield obj(item)
            if len(items) < 100 and next_link is None:
                return
        raise BoundaryError("GitHub pagination limit exceeded")

    def _issue_path(self, number: int) -> str:
        return f"{self._prefix}/issues/{positive_id(number)}"

    def issue(self, number: int) -> Issue:
        data = obj(self._request("GET", self._issue_path(number)))
        if not {"number", "node_id", "repository_url", "title", "body", "labels"}.issubset(data):
            raise BoundaryError("incomplete GitHub issue")
        if "pull_request" in data:
            raise BoundaryError("pull requests are outside triage scope")
        if text(data.get("repository_url")).casefold() != (API + self._prefix).casefold():
            raise BoundaryError("GitHub repository mismatch")
        if positive_id(data.get("number")) != number:
            raise BoundaryError("GitHub issue mismatch")
        labels = [text(obj(label).get("name")) for label in array(data.get("labels"))]
        return parse_json(
            Issue,
            canonical_json(
                {
                    "repository": self.repository,
                    "number": number,
                    "node_id": data.get("node_id"),
                    "title": data.get("title"),
                    "body": data.get("body"),
                    "labels": labels,
                }
            ),
            max_bytes=MAX_RESPONSE_BYTES,
        )

    def comments(self, number: int) -> tuple[Comment, ...]:
        result: list[Comment] = []
        seen: set[int] = set()
        for item in self._pages(self._issue_path(number) + "/comments"):
            user = obj(item["user"]) if item.get("user") is not None else {}
            comment = parse_json(
                Comment,
                canonical_json(
                    {
                        "id": item.get("id"),
                        "author_login": user.get("login", ""),
                        "author_type": user.get("type", ""),
                        "body": item["body"] if item.get("body") is not None else "",
                    }
                ),
                max_bytes=MAX_RESPONSE_BYTES,
            )
            if comment.id in seen:
                raise BoundaryError("inconsistent comment pagination")
            seen.add(comment.id)
            result.append(comment)
        return tuple(result)

    def timeline(self, number: int) -> tuple[LabelEvent, ...]:
        result: list[LabelEvent] = []
        seen: set[int] = set()
        for item in self._pages(self._issue_path(number) + "/timeline"):
            if item.get("event") not in ("labeled", "unlabeled"):
                continue
            actor = obj(item["actor"]) if item.get("actor") is not None else {}
            event = parse_json(
                LabelEvent,
                canonical_json(
                    {
                        "id": item.get("id"),
                        "event": item["event"],
                        "label": obj(item.get("label")).get("name"),
                        "actor_login": actor.get("login", ""),
                        "actor_type": actor.get("type", ""),
                    }
                ),
            )
            if event.id in seen:
                raise BoundaryError("inconsistent timeline pagination")
            seen.add(event.id)
            result.append(event)
        return tuple(result)

    def labels(self) -> tuple[str, ...]:
        return tuple(text(item.get("name")) for item in self._pages(self._prefix + "/labels"))

    def default_head(self) -> str:
        repo = obj(self._request("GET", self._prefix))
        branch = quote(text(repo.get("default_branch")), safe="")
        ref = obj(self._request("GET", f"{self._prefix}/git/ref/heads/{branch}"))
        commit = obj(ref.get("object"))
        sha = text(commit.get("sha"))
        if commit.get("type") != "commit" or not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise BoundaryError("invalid default branch commit")
        return sha

    def file(self, path: str, ref: str) -> bytes | None:
        if path not in {
            ".github/triage-control.yml",
            "triage/policy.yml",
            "triage/PROMPT.md",
            "triage/inference.yml",
        } or not re.fullmatch(r"[0-9a-f]{40}", ref):
            raise BoundaryError("invalid release file reference")
        try:
            data = obj(self._request("GET", f"{self._prefix}/contents/{path}", params={"ref": ref}))
        except GitHubError as error:
            if error.status == 404:
                return None
            raise
        if (
            data.get("type") != "file"
            or data.get("path") != path
            or data.get("encoding") != "base64"
        ):
            raise BoundaryError("invalid release file")
        try:
            content = base64.b64decode("".join(text(data.get("content")).split()), validate=True)
        except (ValueError, binascii.Error):
            raise BoundaryError("invalid release content") from None
        if len(content) > 64 * 1024:
            raise BoundaryError("release file exceeds size limit")
        return content

    def related_candidates(self, issue: Issue, today: date) -> tuple[tuple[int, str], ...]:
        tokens = re.findall(r"[a-z]{3,24}", issue.title.casefold())
        tokens = [t for t in tokens if t not in {"the", "and", "for", "with", "this", "that"}]
        selected = sorted(Counter(tokens), key=lambda t: (-tokens.count(t), t))[:6]
        if not selected:
            return ()
        since = (today - timedelta(days=365)).isoformat()
        query = f"repo:{self.repository} is:issue updated:>={since} " + " ".join(selected)
        data = obj(self._request("GET", "/search/issues", params={"q": query, "per_page": 10}))
        candidates: dict[int, str] = {}
        for item in array(data.get("items"))[:10]:
            hit = obj(item)
            number = positive_id(hit.get("number"))
            if (
                number != issue.number
                and "pull_request" not in hit
                and hit.get("repository_url") == API + self._prefix
            ):
                candidates[number] = text(hit.get("title"))[:200]
        return tuple(candidates.items())

    def create_comment(self, number: int, body: str) -> int:
        response = obj(
            self._request(
                "POST",
                self._issue_path(number) + "/comments",
                payload={"body": body},
                operation="create_comment",
                issue=number,
            )
        )
        return positive_id(response.get("id"))

    def edit_comment(self, number: int, comment_id: int, body: str) -> None:
        path = f"{self._prefix}/issues/comments/{positive_id(comment_id)}"
        target = obj(self._request("GET", path))
        if target.get("issue_url") != API + self._issue_path(number):
            raise BoundaryError("comment target issue mismatch")
        self._request("PATCH", path, payload={"body": body}, operation="edit_comment", issue=number)

    def add_label(self, number: int, label: str) -> None:
        self._request(
            "POST",
            self._issue_path(number) + "/labels",
            payload={"labels": [label]},
            operation="add_label",
            issue=number,
        )

    def remove_label(self, number: int, label: str) -> None:
        segment = "%2E" * len(label) if label in {".", ".."} else quote(label, safe="")
        path = self._issue_path(number) + "/labels/" + segment
        self._request("DELETE", path, operation="remove_label", issue=number)

    def create_label(self, name: str, *, color: str = "ededed") -> None:
        if not re.fullmatch(r"[0-9a-f]{6}", color):
            raise BoundaryError("invalid label color")
        self._request(
            "POST",
            self._prefix + "/labels",
            payload={"name": name, "color": color},
            operation="create_label",
        )
