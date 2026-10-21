---
id: DATAIO-032
title: 'Publish tags a version only on a green CI: the gate of a release runs in Gitea
  Actions'
status: done
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
- tests/test_ci.py
- tests/test_scripts.py
test_paths:
- tests/test_ci.py
- tests/test_scripts.py
docs: none
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
- uv run pytest --no-cov tests/test_ci.py tests/test_scripts.py
resident: null
tool: null
pr: null
translation: 'Перевести гейт выпуска dataio на CI проекта: ci.yml запускается и на
  ветках antagor/publish-*, в [publish] antagor.toml — gate = remote и gate_status_url
  Gitea. Тесты test_ci.py и test_antagor_project_config — первыми. Тег гейта не трогать.'
---

Switch dataio's publish gate to the project's CI (Antagor main@575b2a6, IDEA-312/314): `antagor publish` then
pushes the candidate to the branch `antagor/publish-{commit}`, waits for the CI commit status, and tags only on a
green CI. Until the Human runs `remote-gate-accept`, the local gate runs as before.

## Do

1. `.gitea/workflows/ci.yml`: add `antagor/publish-*` to `on.push.branches` (next to `main`). Gitea Actions sets the
   commit status by itself; nothing else changes in the workflow.
2. `.agents/antagor/antagor.toml`: the Architect already added to `[publish]` `gate = "remote"` and
   `gate_status_url = "https://homeserver.tailee01ab.ts.net:3000/api/v1/repos/bolandeu/dataio/commits/{commit}/status"`
   (Antagor's own file: only the Architect changes it on main). Do not edit it.
3. Tests first:
   - `tests/test_ci.py`: the workflow runs on a push to `main` and to `antagor/publish-*`. PyYAML (YAML 1.1) reads the
     key `on` as the boolean `True`: read `workflow[True]` (or `workflow.get("on", workflow.get(True))`).
   - `tests/test_scripts.py::test_antagor_project_config`: the requirement changed; the expected `publish` table gets
     the two new keys.

The status URL is public and answers now:
`curl -s https://homeserver.tailee01ab.ts.net:3000/api/v1/repos/bolandeu/dataio/commits/<sha>/status` gives
`{"state": "failure", "statuses": [{"context": "ci / gate (push)", ...}]}` for v0.1.28.

## Read first

- `.agents/antagor/antagor.toml` — the `[publish]` table that `test_antagor_project_config` checks

## Out of scope

- the gate tag v1.25.0 in every file: a new tag comes with cli-generator CG-057
- src/, README.md, AGENTS.md
- `.agents/antagor/antagor.toml`: the Architect has changed it on main
