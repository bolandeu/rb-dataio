"""The repo's own tooling scripts: the parts of their logic that decide what the gate demands."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from types import ModuleType

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
GATE = (
    'uvx --from "git+https://homeserver.tailee01ab.ts.net:3000/bolandeu/cli-generator.git'
    '@v1.25.8#subdirectory=gate" rb-release check'
)


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_antagor_project_config() -> None:
    import tomllib

    root = SCRIPTS.parent
    config = tomllib.loads((root / ".agents" / "antagor" / "antagor.toml").read_text())
    assert config["schema"] == 1
    # The prefix must equal the Plane project identifier (DATAIO here), so it may be longer than 4 letters.
    assert re.fullmatch(r"[A-Z]{2,12}", config["prefix"])
    assert config["worker"] == "claude-code"
    assert config["checks"] == ["python3 scripts/check_command_docstrings.py", GATE]
    assert config["review"]["required_types"] == ["feature", "bugfix"]
    assert config["publish"] == {
        "versioning": "semver",
        "changelog": "CHANGELOG.md",
        "deploy_command": "sh scripts/deploy.sh",
        "regenerate": {"uv.lock": "uv lock"},
        "gate": "remote",
        "gate_status_url": "https://homeserver.tailee01ab.ts.net:3000/api/v1/repos/bolandeu/dataio/commits/{commit}/status",
    }
    # The Human sets the mode (`antagor mode set`); dataio runs in `fast`.
    assert config.get("mode") in (None, "strict", "default", "free", "fast")
    # Antagor owns this file and may add entries on upgrade.
    assert {"state/", "receipts/"} <= set((root / ".agents" / "antagor" / ".gitignore").read_text().split())
    assert "ANTAGOR_VERSION" in (SCRIPTS / "deploy.sh").read_text()


def test_antagor_layout() -> None:
    # The method's layout: AGENTS.md holds pointers only, the rules live in their own files (`antagor layout check` runs in check_template.sh).
    root = SCRIPTS.parent
    for name in ("AGENTS.md", "CLAUDE.md", "CONTEXT.md", "CODING_STANDARDS.md", "docs/adr/README.md"):
        assert (root / name).is_file(), name
    agents = (root / "AGENTS.md").read_text()
    for pointer in ("`CONTEXT.md`", "`docs/adr/`", "`CODING_STANDARDS.md`", "`.agents/antagor/`"):
        assert pointer in agents
    for moved in ("TDD", "--dry-run", "expand/contract"):
        assert moved not in agents, moved
    assert "AGENTS.md" in (root / "CLAUDE.md").read_text()
    context = (root / "CONTEXT.md").read_text()
    assert re.fullmatch(r"# \S.*", context.splitlines()[0])
    assert re.search(r"^\*\*[^*]+\*\*:$", re.sub(r"<!--.*?-->", "", context, flags=re.DOTALL), re.MULTILINE)
    readme = (root / "README.md").read_text()
    assert "antagor publish" in readme
    assert "install_hooks" not in readme
    assert "towncrier" not in readme


def test_docstring_check_reads_the_working_tree_only() -> None:
    import inspect

    check = _load("check_command_docstrings")
    assert list(inspect.signature(check.stale_commands).parameters) == ["paths"]
    assert "index" not in (check.stale_commands.__doc__ or "")
