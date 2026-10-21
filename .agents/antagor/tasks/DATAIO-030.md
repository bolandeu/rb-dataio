---
id: DATAIO-030
title: Docs and comments name the Standard's sections, not cli-generator's internal
  files
status: in_review
attempts: 1
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
- .github/dependabot.yml
- .gitleaks.toml
- README.md
- pyproject.toml
- scripts/check_command_docstrings.py
- src/rb_dataio/_distribution.py
- src/rb_dataio/commands/auth.py
- src/rb_dataio/commands/login.py
- src/rb_dataio/core/deps.py
- src/rb_dataio/core/errors.py
- src/rb_dataio/core/opencli.py
- src/rb_dataio/core/version.py
- src/rb_dataio/credentials/health.py
- src/rb_dataio/credentials/manager.py
- src/rb_dataio/data/SKILL.md
- src/rb_dataio/providers/http.py
- tests/contracts/schema.json
- tests/test_auth.py
- tests/test_contracts.py
- tests/test_describe.py
- tests/snapshots/**
test_paths: []
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
- sh -c "! git grep -n -E 'architecture\.md|conventions\.md|help-standard\.md|standard-release\.md|plugin.s
  README|standard §|§ ?[0-9]|release\.py' -- src scripts tests README.md pyproject.toml
  .gitleaks.toml .github CODING_STANDARDS.md AGENTS.md"
resident: null
tool: null
pr: null
translation: 'Убрать из комментариев, docstring и README ссылки на внутреннюю разработку
  cli-generator: несуществующие architecture.md, conventions.md, help-standard.md,
  tools/docs/standard-release.md, номера разделов Стандарта (§8, §10, §12) и старый
  гейт release.py. Каждую ссылку заменить разделом Стандарта по имени («the Standard,
  Health»), правилом простыми словами или убрать. Где строка совпадает с шаблоном
  — формулировка шаблона v1.25.2. Поведение не меняется.'
---

dataio is a product with its own docs and `docs/adr/`. Its comments, docstrings and README still point at the
development of cli-generator: reference files that no longer exist (`architecture.md` with §N, `conventions.md`,
`help-standard.md`, the plugin's README), a tools doc that does not exist (`tools/docs/standard-release.md` §N),
numbered sections of the Standard (`standard §8`, `§10`, `§12`), and the old gate `release.py`, which DATAIO-029
removed. Template v1.25.2 of cli-generator removed the same lines from the template. Comments, docstrings and docs
only: no behaviour changes.

## The rule for each line

Replace each reference with one of:

1. the Standard's section by its name: «the Standard, Health», «the Standard, Technology»;
2. the rule in plain words;
3. nothing, when the reference adds nothing.

The Standard's sections: Technology, Commands, Output, Errors, Health, Credentials, Install, Docs, CI, Release,
and under Optional parts: Project, Credentials and providers, HTTP, Database, Package skill, Describe,
Consumer contracts, Detach. The old gate `release.py --check` becomes `rb-release check`.

Where a line is the same as in the template, take the template's v1.25.2 wording:
`git -C /Users/bolandau/Work/tools/cli-generator diff v1.25.0 v1.25.2 -- template/`.
Other lines (dataio's own, for example `tools/docs/standard-release.md §8` → «the Standard, Health»):
use the same rule.

## The lines (31 in 20 files, `git grep` on main)

- `.github/dependabot.yml:1` (`standard-release.md §6`: drop the reference)
- `.gitleaks.toml:1`
- `README.md:90-91`, `README.md:95`
- `pyproject.toml:73`, `pyproject.toml:98`
- `scripts/check_command_docstrings.py:5`
- `src/rb_dataio/_distribution.py:2`, `:8`
- `src/rb_dataio/commands/auth.py:12`, `src/rb_dataio/commands/login.py:4`
- `src/rb_dataio/core/deps.py:11`, `:37`, `:143`
- `src/rb_dataio/core/errors.py:25`, `:112`
- `src/rb_dataio/core/opencli.py:15`, `src/rb_dataio/core/version.py:47`
- `src/rb_dataio/credentials/health.py:1`, `:21`, `:101`, `:157`
- `src/rb_dataio/credentials/manager.py:287`
- `src/rb_dataio/data/SKILL.md:21` («never a branch: standard §9» → «never a branch»)
- `src/rb_dataio/providers/http.py:25`
- `tests/contracts/schema.json:5` (the template's v1.25.2 text)
- `tests/test_auth.py:76` («the §8 shape» → «the auth status shape»)
- `tests/test_contracts.py:5`, `:20` (`rb-release check`), `:51` (the template's «The version the gate is building,
  when set, else the installed one.»)
- `tests/test_describe.py:9`

## Keep

- The `[tool.cli-generator]` key in `pyproject.toml`: a real setting.
- Code, values and behaviour. A help snapshot or the `--ai` output may change only if `SKILL.md` text is in it:
  then update the snapshot with `uv run pytest --snapshot-update` and read the diff.
- Rewrap a changed comment to the line length of its file (120), nothing else.

## Basis

cli-generator template v1.25.2 made the same edits in the template: git -C /Users/bolandau/Work/tools/cli-generator diff v1.25.0 v1.25.2 -- template/. The Standard's section names: skills/cli-builder/reference/standard.md of tag v1.25.2.

## Read first

- `CODING_STANDARDS.md`

## Out of scope

- any change of code, values or behaviour
- docs/ (docs/brief.md, docs/adr/, docs/SPEC.md, docs/plans/), CHANGELOG.md, .agents/, AGENTS.md: dataio's own history and contract
- the [tool.cli-generator] key of pyproject.toml
- copier update, .copier-answers.yml

## Feedback

### Attempt 1: file docstring

- add a docstring to src/rb_dataio/_distribution.py: what it holds and why
- add a docstring to src/rb_dataio/commands/auth.py: what it holds and why
- add a docstring to src/rb_dataio/core/version.py: what it holds and why
