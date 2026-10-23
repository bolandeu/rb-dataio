---
id: DATAIO-040
title: 'Template update v1.15.0 -> v1.27.1: apply the merged patch'
status: ideas
attempts: 0
blocked: false
blocked_reason: null
phase: null
tests_hash: null
publish_stage: null
created_by: architect
approved_by: null
worker: claude-code
type: chore
owns_paths:
- .copier-answers.yml
- .gitea
- .github
- .gitignore
- pyproject.toml
- uv.lock
- scripts/detach.py
- src/rb_dataio
- tests
- docs/plans
test_paths: []
docs:
- src/rb_dataio/data/SKILL.md
tools: []
worker_args: null
decision: false
visual: null
depends_on: []
budget_usd: null
epic: null
spec_refs: []
checks:
- uv lock --check
- uv run pytest -q
- uv run ruff check .
- uv run ruff format --check .
resident: null
tool: null
pr: null
---

The patch /Users/bolandau/Work/tools/dataio/docs/plans/template-v1.27.1.patch is the verified 3-way merge of the cli-generator template v1.27.1 into dataio (795 tests pass, ruff clean, made on a copy). Apply it with 'git apply' from the repo root, then delete docs/plans/template-v1.27.1.patch in the same commit. Delete the empty .github/ directory if it remains (test_no_github_workflow fails while it exists). Do not edit the patched code by hand beyond fixing a check that fails; if one fails, report which and why. Run the three checks. Known and accepted: with no project, doctor now prints the template wording 'doctor runs outside a project'.

## Out of scope

- AGENTS.md, CODING_STANDARDS.md, CONTEXT.md, CHANGELOG.md, .agents/antagor/antagor.toml, scripts/deploy.sh, uv.lock
- Python 3.14-only syntax: keep requires-python >=3.11 and write except (A, B):
- Any change of the package's own commands, public API or error catalogue
