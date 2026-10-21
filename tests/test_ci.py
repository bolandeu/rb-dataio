"""The Gitea Actions workflow: it runs the gate of the template tag (the Standard, CI)."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".gitea" / "workflows" / "ci.yml"
# The tag of the gate, not `_commit` of .copier-answers.yml: that stays at the generated version until a `copier update`.
GATE_TAG = "v1.25.0"
GATE = (
    'uvx --from "git+https://homeserver.tailee01ab.ts.net:3000/bolandeu/cli-generator.git'
    f'@{GATE_TAG}#subdirectory=gate" rb-release check'
)


def test_workflow_runs_the_gate_on_the_docker_runner() -> None:
    job = yaml.safe_load(WORKFLOW.read_text())["jobs"]["gate"]
    assert job["runs-on"] == "docker"
    checkout = next(step for step in job["steps"] if str(step.get("uses", "")).startswith("actions/checkout@"))
    assert checkout["with"]["fetch-depth"] == 0
    assert job["steps"][-1]["run"].strip() == GATE
