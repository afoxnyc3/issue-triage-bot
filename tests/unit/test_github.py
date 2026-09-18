import base64
import json
from datetime import date

import httpx
import pytest

from issue_triage_bot.codec import BoundaryError
from issue_triage_bot.github import GitHub, GitHubError


def issue_data(**updates):
    return {
        "number": 12,
        "node_id": "I_fixture",
        "repository_url": "https://api.github.com/repos/example/repo",
        "title": "Crash repo:attacker/other OR is:pr",
        "body": None,
        "labels": [{"name": "human"}],
    } | updates


def client(handler, **options):
    return GitHub(
        "example/repo",
        "noncredential-fixture",
        transport=httpx.MockTransport(handler),
        sleep=lambda _: None,
        **options,
    )


def test_issue_normalization_and_extra_api_metadata():
    github = client(
        lambda _: httpx.Response(200, json=issue_data(extra="allowed GitHub API extension"))
    )
    issue = github.issue(12)
    assert issue.body is None and issue.labels == ("human",)


@pytest.mark.parametrize(
    "update",
    [
        {"number": 13},
        {"number": True},
        {"pull_request": {}},
        {"repository_url": "https://evil.example/repo"},
        {"labels": ["bug"]},
    ],
)
def test_wrong_issue_or_schema_rejected(update):
    github = client(lambda _: httpx.Response(200, json=issue_data(**update)))
    with pytest.raises(BoundaryError):
        github.issue(12)


def test_complete_pagination_with_local_page_construction():
    requests = []

    def handler(request):
        requests.append(str(request.url))
        page = int(request.url.params["page"])
        rows = [
            {"id": i, "body": "comment", "user": {"login": "human", "type": "User"}}
            for i in (range(1, 101) if page == 1 else [101])
        ]
        return httpx.Response(200, json=rows)

    comments = client(handler).comments(12)
    assert len(comments) == 101 and len(requests) == 2
    assert all(url.startswith("https://api.github.com/repos/example/repo/") for url in requests)


def test_incomplete_pagination_fails_closed():
    def handler(request):
        if request.url.params["page"] == "1":
            return httpx.Response(
                200, json=[{"id": i, "body": "text", "user": None} for i in range(1, 101)]
            )
        return httpx.Response(500, json={"message": "private issue body"})

    with pytest.raises(GitHubError) as error:
        client(handler).comments(12)
    assert "private issue" not in str(error.value)


@pytest.mark.parametrize(
    "status,headers,body,expected",
    [
        (429, {}, {}, True),
        (500, {}, {}, True),
        (403, {"Retry-After": "1"}, {}, True),
        (403, {}, {"message": "You have exceeded a secondary rate limit"}, True),
        (403, {}, {"message": "forbidden"}, False),
        (404, {}, {}, False),
        (422, {}, {}, False),
    ],
)
def test_retry_classification(status, headers, body, expected):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, headers=headers, json=body)

    with pytest.raises(GitHubError) as error:
        client(handler).issue(12)
    assert error.value.transient is expected
    assert len(calls) == (3 if expected else 1)


def test_long_retry_after_does_not_sleep_or_hammer():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429, headers={"Retry-After": "3600"})

    with pytest.raises(GitHubError):
        client(handler).issue(12)
    assert len(calls) == 1


def test_healthy_retry_after_transient():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(502) if len(calls) < 3 else httpx.Response(200, json=issue_data())

    assert client(handler).issue(12).number == 12
    assert len(calls) == 3


def test_writes_need_guard_and_lost_response_is_not_replayed():
    calls = []
    guards = []

    def handler(request):
        calls.append(request)
        raise httpx.ReadError("untrusted transport error payload")

    github = client(handler)
    with pytest.raises(BoundaryError, match="read-only"):
        github.create_comment(12, "safe")
    assert not calls
    github = client(handler, write_guard=lambda op, number: guards.append((op, number)))
    with pytest.raises(GitHubError) as error:
        github.create_comment(12, "safe")
    assert error.value.uncertain and error.value.transient
    assert len(calls) == 1 and guards == [("create_comment", 12)]
    assert "untrusted" not in str(error.value)


def test_failed_guard_prevents_http_mutation():
    def denied(*_):
        raise BoundaryError("disabled")

    def unexpected(_):
        raise AssertionError("request should not occur")

    with pytest.raises(BoundaryError, match="disabled"):
        client(unexpected, write_guard=denied).add_label(12, "bug")


def test_edit_comment_checks_target_issue():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200, json={"issue_url": "https://api.github.com/repos/example/repo/issues/99"}
        )

    github = client(handler, write_guard=lambda *_: None)
    with pytest.raises(BoundaryError, match="target"):
        github.edit_comment(12, 3, "safe")
    assert all(r.method == "GET" for r in requests)


def test_read_release_from_immutable_head():
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path.endswith("/repos/example/repo"):
            return httpx.Response(200, json={"default_branch": "release/main"})
        if "/git/ref/heads/" in request.url.path:
            return httpx.Response(200, json={"object": {"type": "commit", "sha": "a" * 40}})
        assert request.url.params["ref"] == "a" * 40
        return httpx.Response(
            200,
            json={
                "type": "file",
                "path": "triage/policy.yml",
                "encoding": "base64",
                "content": base64.b64encode(b"rollout: dry_run").decode(),
            },
        )

    github = client(handler)
    assert github.file("triage/policy.yml", github.default_head()) == b"rollout: dry_run"
    assert len(requests) == 3


def test_redirects_not_followed_and_body_not_echoed():
    def handler(_):
        return httpx.Response(302, headers={"Location": "https://evil.example"}, text="private")

    with pytest.raises(GitHubError) as error:
        client(handler).issue(12)
    assert "private" not in str(error.value)


def test_timeline_only_label_events_and_deleted_actor():
    rows = [
        {"event": "commented"},
        {"id": 5, "event": "unlabeled", "label": {"name": "bug"}, "actor": None},
    ]
    events = client(lambda _: httpx.Response(200, json=rows)).timeline(12)
    assert len(events) == 1 and not events[0].by_bot


def test_related_query_cannot_accept_issue_supplied_qualifiers(issue):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "items": [
                    issue_data(number=8),
                    issue_data(number=12),
                    issue_data(number=9, repository_url="other"),
                ]
            },
        )

    github = client(handler)
    hostile = type(issue)(
        **(issue.model_dump() | {"title": "repo:attacker/other OR is:pr updated:>1900 crash"})
    )
    candidates = github.related_candidates(hostile, date(2026, 9, 18))
    assert [n for n, _ in candidates] == [8]
    query = calls[0].url.params["q"]
    assert query.startswith("repo:example/repo is:issue updated:>=2025-09-18 ")
    assert query.count("repo:") == 1 and query.count("is:") == 1
    assert "attacker/other" not in query and query.count("updated:") == 1


def test_each_write_has_narrow_body_and_guard():
    requests = []
    guards = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=[])

    github = client(handler, write_guard=lambda *args: guards.append(args))
    github.add_label(12, "bug")
    github.remove_label(12, "type:docs/extra")
    assert json.loads(requests[0].content) == {"labels": ["bug"]}
    assert requests[1].method == "DELETE" and b"type%3Adocs%2Fextra" in requests[1].url.raw_path
    assert guards == [("add_label", 12), ("remove_label", 12)]


def test_short_page_with_next_link_is_not_truncated():
    calls = []

    def handler(request):
        calls.append(request)
        page = int(request.url.params["page"])
        link = {
            "Link": (
                '<https://api.github.com/repos/example/repo/issues/12/comments?page=2>; rel="next"'
            )
        }
        return httpx.Response(
            200, json=[{"id": page, "body": "ok", "user": None}], headers=link if page == 1 else {}
        )

    assert len(client(handler).comments(12)) == 2
    assert len(calls) == 2


def test_cross_origin_pagination_rejected_without_following():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            200, json=[], headers={"Link": '<https://evil.test/?page=2>; rel="next"'}
        )

    with pytest.raises(BoundaryError, match="pagination link"):
        client(handler).comments(12)
    assert len(calls) == 1


def test_dot_segment_label_is_encoded_without_path_traversal():
    paths = []

    def handler(request):
        paths.append(request.url.raw_path)
        return httpx.Response(204)

    github = client(handler, write_guard=lambda *_: None)
    github.remove_label(12, "..")
    assert paths == [b"/repos/example/repo/issues/12/labels/%2E%2E"]


def test_duplicate_api_json_keys_fail_closed():
    with pytest.raises(BoundaryError):
        client(lambda _: httpx.Response(200, content=b'{"number":12,"number":13}')).issue(12)
