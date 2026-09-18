import base64
import json
import secrets

import pytest
from typer.testing import CliRunner

from issue_triage_bot import cli
from issue_triage_bot.codec import canonical_json
from tests.fakes import Repo, prepare

runner = CliRunner()


class Client:
    def __init__(self, repo, guard):
        self.repo, self.guard = repo, guard

    def __getattr__(self, name):
        return getattr(self.repo, name)

    def close(self):
        pass

    def related_candidates(self, *_):
        return ((8, "Related"),)

    def issue_numbers(self, limit=51):
        return (12,)

    def labels(self):
        return tuple(self.repo.known_labels)

    def create_label(self, name):
        self.guard("create_label", None)
        self.repo.known_labels.add(name)

    def create_comment(self, number, body):
        self.guard("create_comment", number)
        return self.repo.create_comment(number, body)

    def edit_comment(self, number, id, body):
        self.guard("edit_comment", number)
        self.repo.edit_comment(number, id, body)

    def add_label(self, number, label):
        self.guard("add_label", number)
        self.repo.add_label(number, label)

    def remove_label(self, number, label):
        self.guard("remove_label", number)
        self.repo.remove_label(number, label)


@pytest.fixture
def environment(monkeypatch):
    # Never read host workflow credentials; isolate the entire runtime environment.
    monkeypatch.setattr(cli.os, "environ", {})
    monkeypatch.setenv("GITHUB_REPOSITORY", "example/repo")
    monkeypatch.setenv("TRIAGE_STATE_HMAC_KEY_ID", "fixture")
    monkeypatch.setenv("TRIAGE_STATE_HMAC_KEY", base64.b64encode(secrets.token_bytes(32)).decode())
    repo = Repo()
    repo.known_labels = set()
    monkeypatch.setattr(cli, "_client", lambda repository, guard=None: Client(repo, guard))
    return repo


def test_apply_fixture_default_dry_run(environment, decision, tmp_path):
    path = tmp_path / "decision.json"
    path.write_text(decision.model_dump_json())
    audit = tmp_path / "audit.json"
    result = runner.invoke(
        cli.app, ["apply", "--issue", "12", "--input", str(path), "--audit", str(audit)]
    )
    assert result.exit_code == 0, result.output
    record = json.loads(result.stdout)
    assert record["status"] == "dry_run"
    assert any(op["label"] == "bug" for op in record["operations"])
    assert record["decision_hash"] and record["intended_outcome"] == "applied"
    assert json.loads(audit.read_text()) == record and environment.writes == []


def test_write_requires_context_and_envelope(environment, decision, tmp_path):
    path = tmp_path / "decision.json"
    path.write_text(decision.model_dump_json())
    result = runner.invoke(cli.app, ["apply", "--issue", "12", "--input", str(path), "--write"])
    assert result.exit_code == 1 and "trusted workflow context" in result.output
    assert not environment.writes


def workflow_environment(monkeypatch, tmp_path):
    event = tmp_path / "event.json"
    event.write_bytes(
        canonical_json(
            {
                "repository": {"full_name": "example/repo"},
                "issue": {"number": 12, "node_id": "I_fixture"},
            }
        )
    )
    for key, value in {
        "GITHUB_RUN_ID": "100",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_EVENT_NAME": "issues",
        "GITHUB_EVENT_PATH": str(event),
    }.items():
        monkeypatch.setenv(key, value)


def test_concrete_guard_wired_for_comment_only_apply(environment, decision, tmp_path, monkeypatch):
    workflow_environment(monkeypatch, tmp_path)
    environment.files["triage/policy.yml"] = environment.files["triage/policy.yml"].replace(
        b"rollout: type_labels", b"rollout: comment_only"
    )
    environment.files[".github/triage-control.yml"] = b"enabled: true\npolicy_generation: 1\n"
    envelope, _ = prepare(environment)
    env_file = tmp_path / "envelope.json"
    env_file.write_text(envelope.model_dump_json())
    proposal = tmp_path / "proposal.json"
    proposal.write_text(decision.model_dump_json())
    result = runner.invoke(
        cli.app,
        [
            "apply",
            "--issue",
            "12",
            "--input",
            str(proposal),
            "--envelope",
            str(env_file),
            "--write",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["status"] == "applied"
    assert environment.writes == ["create_comment", "edit_comment"]


def test_event_identity_mismatch_rejected(environment, tmp_path, monkeypatch):
    workflow_environment(monkeypatch, tmp_path)
    monkeypatch.setenv("GITHUB_REPOSITORY", "wrong/repo")
    result = runner.invoke(cli.app, ["apply", "--repo", "example/repo", "--issue", "12", "--write"])
    assert result.exit_code == 1 and environment.writes == []


def test_check_and_setup_labels_default_no_writes(environment):
    result = runner.invoke(cli.app, ["check"])
    assert result.exit_code == 1 and "bug" in json.loads(result.stdout)["missing_labels"]
    result = runner.invoke(cli.app, ["setup-labels"])
    assert result.exit_code == 0 and not environment.known_labels
    result = runner.invoke(cli.app, ["setup-labels", "--write"])
    assert result.exit_code == 0, result.output
    assert "bug" in environment.known_labels
    assert runner.invoke(cli.app, ["check"]).exit_code == 0


def test_setup_labels_kill_switch_blocks_write(environment):
    environment.files[".github/triage-control.yml"] = b"enabled: false\npolicy_generation: 1"
    result = runner.invoke(cli.app, ["setup-labels", "--write"])
    assert result.exit_code == 1 and not environment.known_labels


def test_repair_is_read_only(environment):
    result = runner.invoke(cli.app, ["repair", "--issue", "12", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["dry_run"] and not environment.writes


def test_secret_configuration_error_never_echoes_value(environment, monkeypatch):
    marker = "credential-canary-that-must-never-be-printed"
    monkeypatch.setenv("TRIAGE_STATE_HMAC_KEY", marker)
    result = runner.invoke(cli.app, ["apply", "--issue", "12"])
    assert result.exit_code == 1 and marker not in result.output
    assert "invalid state signing" in result.output


def test_disabled_apply_does_not_load_state_key(environment, monkeypatch):
    environment.files[".github/triage-control.yml"] = b"enabled: false\npolicy_generation: 1"
    monkeypatch.delenv("TRIAGE_STATE_HMAC_KEY")
    result = runner.invoke(cli.app, ["apply", "--issue", "12"])
    assert result.exit_code == 0 and json.loads(result.stdout)["status"] == "disabled"


def test_repair_without_issue_lists_repository(environment):
    result = runner.invoke(cli.app, ["repair", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["issues"][0]["issue_number"] == 12
    assert not environment.writes


def test_setup_labels_refences_release_before_every_write(environment, monkeypatch):
    original = Client.create_label

    def change_after_first(self, name):
        original(self, name)
        self.repo.files["triage/PROMPT.md"] += b" changed"

    monkeypatch.setattr(Client, "create_label", change_after_first)
    result = runner.invoke(cli.app, ["setup-labels", "--write"])
    assert result.exit_code == 1 and len(environment.known_labels) == 1
    assert "live control or policy change" in result.output
