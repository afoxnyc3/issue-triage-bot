from pathlib import Path

import pytest

from issue_triage_bot.codec import BoundaryError
from issue_triage_bot.release import load_live, schema_bytes


class Reader:
    def __init__(self):
        self.files = {
            path: Path(path).read_bytes()
            for path in [
                ".github/triage-control.yml",
                "triage/policy.yml",
                "triage/inference.yml",
                "triage/PROMPT.md",
            ]
        }
        self.files[".github/triage-control.yml"] = b"enabled: true\npolicy_generation: 1\n"
        self.head = "a" * 40
        self.reads = []

    def default_head(self):
        return self.head

    def file(self, path, ref):
        self.reads.append((path, ref))
        return self.files.get(path)


def test_committed_schema_matches_runtime():
    assert Path("triage/schema.json").read_bytes() == schema_bytes() + b"\n"


def test_live_release_all_files_share_immutable_head():
    reader = Reader()
    release = load_live(reader)
    assert release.identity.model == "claude-sonnet-4-6"
    assert release.identity.policy_generation == 1
    assert len(reader.reads) == 4 and {ref for _, ref in reader.reads} == {"a" * 40}
    assert release.policy.rollout == "dry_run"


@pytest.mark.parametrize("control", [None, b"enabled: false\npolicy_generation: 1"])
def test_disabled_or_absent_control_stops_before_policy(control):
    reader = Reader()
    reader.files[".github/triage-control.yml"] = control
    assert load_live(reader) is None
    assert len(reader.reads) == 1


@pytest.mark.parametrize("path", ["triage/policy.yml", "triage/PROMPT.md", "triage/inference.yml"])
def test_missing_required_file_fails_closed(path):
    reader = Reader()
    del reader.files[path]
    with pytest.raises(BoundaryError, match="incomplete"):
        load_live(reader)


@pytest.mark.parametrize(
    "path",
    [".github/triage-control.yml", "triage/policy.yml", "triage/PROMPT.md", "triage/inference.yml"],
)
def test_content_drift_changes_fence_without_generation_bump(path):
    reader = Reader()
    before = load_live(reader)
    reader.files[path] += b"\n# changed\n"
    after = load_live(reader)
    assert before.identity != after.identity


def test_schema_drift_rejected_before_use():
    reader = Reader()
    raw = reader.files["triage/inference.yml"]
    reader.files["triage/inference.yml"] = raw[: raw.index(b"decision_schema_digest:")] + (
        b'decision_schema_digest: "' + b"0" * 64 + b'"\n'
    )
    with pytest.raises(BoundaryError, match="schema"):
        load_live(reader)


def test_type_label_mode_requires_canary():
    reader = Reader()
    reader.files["triage/policy.yml"] = reader.files["triage/policy.yml"].replace(
        b"dry_run", b"type_labels"
    )
    with pytest.raises(BoundaryError, match="canary"):
        load_live(reader)
    reader.files[".github/triage-control.yml"] += (
        b"canary:\n  first_issue: 12\n  max_issues: 20\n  max_mutations: 60\n"
    )
    assert load_live(reader).control.canary.max_mutations == 60


@pytest.mark.parametrize(
    "old,new",
    [
        (b"schema_version: 1", b"schema_version: true"),
        (b"max_turns: 2", b"max_turns: 2.0"),
        (b"strict_mcp_config: true", b"strict_mcp_config: 1"),
        (b"disallowed_tools: mcp__*", b"disallowed_tools: Read"),
        (b"tools_argument: --tools=", b"tools_argument: --tools Read"),
    ],
)
def test_inference_contract_cannot_coerce_or_weaken_flags(old, new):
    reader = Reader()
    reader.files["triage/inference.yml"] = reader.files["triage/inference.yml"].replace(old, new)
    with pytest.raises(BoundaryError):
        load_live(reader)
