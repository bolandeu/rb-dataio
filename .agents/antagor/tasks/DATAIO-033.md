---
id: DATAIO-033
title: 'Gate tag v1.25.8: CI on homeserver runs the gate as the Mac does'
status: queue
attempts: 0
blocked: false
blocked_reason: null
phase: null
tests_hash: null
publish_stage: null
created_by: architect
approved_by: human
worker: claude-code
type: chore
owns_paths:
- .gitea/workflows/ci.yml
- README.md
- tests/test_ci.py
- tests/test_scripts.py
test_paths:
- tests/test_ci.py
docs:
- README.md
tools: []
worker_args: null
class: mechanical
decision: false
visual: null
depends_on: []
budget_usd: null
epic: null
spec_refs: []
checks:
- uv run pytest --no-cov tests/test_ci.py
- sh -c "! git grep -n 'v1\.25\.0' -- .gitea README.md tests AGENTS.md .agents/antagor/antagor.toml"
resident: null
tool: null
pr: null
translation: Поднять тег гейта cli-generator с v1.25.0 до v1.25.8 в ci.yml, README.md,
  tests/test_ci.py и tests/test_scripts.py. v1.25.8 работает на Python >=3.11 и чинит
  гейт в CI. antagor.toml и AGENTS.md Архитектор уже поправил. requires-python остаётся
  >=3.11.
---

Bump the gate tag from v1.25.0 to v1.25.8 (cli-generator). v1.25.8 runs on Python >=3.11 and fixes the gate in CI:
the standard steps probe the installed CLI without GITHUB_ACTIONS/FORCE_COLOR/PY_COLORS, and the pytest step runs
with them. The Architect checked it: on main + DATAIO-031 + DATAIO-032 + this bump, with GITHUB_ACTIONS=true and
UV_PYTHON=3.11, the gate v1.25.8 ends with `release: gate passed`.

## Do

Replace `v1.25.0` with `v1.25.8` in the gate command (and its comment) of:

1. `.gitea/workflows/ci.yml` (the comment line and the uvx line of the step «Gate»);
2. `README.md` (the gate line);
3. `tests/test_ci.py` (`GATE_TAG`);
4. `tests/test_scripts.py` (`GATE`).

The requirement changed (a new gate tag), so the two tests change with it. Nothing else changes:
`requires-python` stays ">=3.11", CI stays on the lowest supported Python.

The Architect already changed `.agents/antagor/antagor.toml` (checks) and `AGENTS.md` on main.

## Note

On main, `tests/test_scripts.py::test_antagor_project_config` is red until DATAIO-032 is merged (it expects the
new `[publish]` table). That is not this task's: the checks of this task do not run it.

## Read first

- `.agents/antagor/antagor.toml` — its `checks` line has the new tag already

## Out of scope

- requires-python and the Python version of CI (the Human: dataio stays on >=3.11)
- .agents/antagor/antagor.toml and AGENTS.md: the Architect changed them on main
- src/ and every other test
