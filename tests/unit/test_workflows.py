import re
from pathlib import Path

import yaml


def test_ci_is_locked_read_only_and_pinned():
    workflow = yaml.load(Path(".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader)
    assert workflow["permissions"] == {"contents": "read"}
    steps = workflow["jobs"]["verify"]["steps"]
    assert any(step.get("run") == "uv sync --locked --group dev" for step in steps)
    for step in steps:
        if "uses" in step:
            assert re.fullmatch(r"[\w/-]+@[0-9a-f]{40}", step["uses"])
    assert steps[0]["with"]["persist-credentials"] == "false"
    assert "secrets." not in Path(".github/workflows/ci.yml").read_text()


def test_legacy_cannot_trigger_or_run():
    workflow = yaml.load(Path(".github/workflows/triage.yml").read_text(), Loader=yaml.BaseLoader)
    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["jobs"]["triage"]["if"] == "${{ false }}"
    assert Path("agent.py").exists()
    assert Path("scripts/memory_manager.py").exists()
    assert Path("supabase/migrations/001_create_memory_tables.sql").exists()
