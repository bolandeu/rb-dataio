---
id: DATAIO-029
title: 'CLI Standard v1.25.0: a usage error under --json prints the INVALID_ARGUMENTS
  envelope; the gate is rb-release check'
status: done
attempts: 1
blocked: false
blocked_reason: null
phase: null
tests_hash: null
publish_stage: null
created_by: architect
approved_by: human
worker: claude-code
type: bugfix
owns_paths:
- .gitleaks.toml
- pyproject.toml
- uv.lock
- src/rb_dataio/output/__init__.py
- src/rb_dataio/cli.py
- .gitea/workflows/ci.yml
- scripts/release.py
- tests/test_scripts.py
- tests/test_cli.py
- tests/test_ci.py
- README.md
test_paths:
- tests/test_cli.py
- tests/test_ci.py
- tests/test_scripts.py
docs:
- README.md
tools: []
worker_args: null
class: standard
decision: false
visual: null
depends_on: []
budget_usd: null
epic: null
spec_refs: []
checks:
- uv run pytest --no-cov tests/test_cli.py tests/test_ci.py tests/test_scripts.py
- uvx --from "git+https://homeserver.tailee01ab.ts.net:3000/bolandeu/cli-generator.git@v1.25.0#subdirectory=gate"
  rb-release check
resident: null
tool: null
pr: null
translation: 'Привести dataio к Стандарту CLI шаблона cli-generator v1.25.0 без copier
  update. Пять красных шагов гейта: secret scan (.gitleaks.toml шаблона с фейковыми
  тестовыми значениями), install section ([tool.rb.install]), standard: errors (ошибка
  использования под --json — конверт INVALID_ARGUMENTS, RootGroup из шаблона), standard:
  ci (.gitea/workflows/ci.yml с uvx-гейтом), vulnerability audit (certifi 2026.10.19).
  Старый гейт scripts/release.py и его тесты удаляются. Тесты — первыми.'
---

Bring dataio to the CLI Standard of cli-generator template v1.25.0, without `copier update`.
The gate is now `uvx --from "git+https://homeserver.tailee01ab.ts.net:3000/bolandeu/cli-generator.git@v1.25.0#subdirectory=gate" rb-release check`
(the Architect already put it in `.agents/antagor/antagor.toml` `checks`). Five gate steps are red on main.
The Architect checked each fix below in a throwaway clone: with all five, the gate ends with `release: gate passed`.

## The red steps and their fixes

1. `secret scan` (Standard, Credentials). gitleaks finds the fake test value `good-secret-123` of
   `tests/test_auth.py` in commit 24a000b. Add the root `.gitleaks.toml` of the template, byte for byte:
   `git -C /Users/bolandau/Work/tools/cli-generator show v1.25.0:template/.gitleaks.toml`.
   It allows `good-secret-123` and `bad-secret-456` as exact strings. It is not a leaked key.
2. `install section` (Standard, Install). Add to `pyproject.toml`, before `[tool.cli-generator]`:
   `[tool.rb.install]`, `homeserver = ["rbtools"]`, `mac = true`. No other key.
3. `standard: errors` (Standard, Errors). A usage error (unknown option, unknown command, missing value) under
   `--json` must print the error envelope `INVALID_ARGUMENTS` on stdout and exit 2. Without `--json` it stays
   Click's usage message on stderr. Now `dataio --json init --rb-release-unknown-option` prints nothing on stdout.
   Port `RootGroup` and `_usage_error` from the template's `output/__init__.py` (v1.25.0) into
   `src/rb_dataio/output/__init__.py`, and set `cls=output.RootGroup` on the Typer app in `src/rb_dataio/cli.py`.
   dataio has no optional-part registration: leave out `part_options`. Take Click's `UsageError` from
   `typer.BadParameter.__bases__[0]`, as the template does.
4. `standard: ci` (Standard, CI). Add `.gitea/workflows/ci.yml`: the template's `ci.yml.jinja` (v1.25.0) with
   `{{ gate_command }}` replaced by the uvx gate command above, tag `v1.25.0`.
5. `vulnerability audit` (Standard, Release). osv-scanner finds PYSEC-2026-4320 in certifi 2026.7.22.
   `uv lock --upgrade-package certifi` (2026.10.19 is fixed). Change nothing else in `uv.lock`.

## The old gate goes

The copied `scripts/release.py` is the old gate. Nothing runs it after this task.

- `git rm scripts/release.py`. In `tests/test_scripts.py` remove the tests of `release.py` (the gate now lives in
  cli-generator and has its own tests). Keep the tests of the other scripts.
- `tests/test_scripts.py::test_antagor_project_config` asserts the old `checks` line. The requirement changed:
  assert the new line `["python3 scripts/check_command_docstrings.py", '<the uvx gate command>']`.
- `pyproject.toml`: remove the `gate_extras` comment lines of `[tool.cli-generator]` (they configure `release.py`).
- `README.md`: the gate line and the two mentions of `release.py --check` name the uvx command.

## Tests first

Commit the failing tests before the code:

- `tests/test_cli.py`: the template's `test_usage_error_under_json_is_the_error_envelope` (parametrized: an unknown
  option on a command, the same with `--json` after the command, an unknown command, a missing option value) and
  `test_usage_error_without_json_stays_on_stderr`, adapted to dataio's commands.
- `tests/test_ci.py`: the workflow runs the uvx gate command at tag `v1.25.0` on the runner `docker`, with
  `fetch-depth: 0`. Pin the tag in the test as a constant. Do not read it from `.copier-answers.yml`: its
  `_commit` stays `v1.15.0`, because this task does not run `copier update`.

## Rules

- Surgical changes: touch only what a red step or the old gate needs. Do not reformat other code.
- Fix the code, not the gate: no blanket ignore, no lowered floor.
- After any `ruff check --fix`, run the whole test suite.
- Run the uvx gate in the worktree until its last line is `release: gate passed`. Put the full list of gate steps
  in the report, and the `existing tests` step output with the reason for each changed test.

## Acceptance

- Given the installed dataio, When `dataio --json init --rb-release-unknown-option` runs, Then stdout is the error envelope with code INVALID_ARGUMENTS and the exit code is 2 [check: tests/test_cli.py]
- Given the installed dataio, When `dataio doctor --no-such-option` runs without --json, Then stdout is empty, the usage message is on stderr and the exit code is 2 [check: tests/test_cli.py]
- Given the repo, When .gitea/workflows/ci.yml is read, Then its last step runs the uvx gate command at tag v1.25.0 on the runner docker with fetch-depth 0 [check: tests/test_ci.py]
- Given the worktree, When the uvx gate of v1.25.0 runs, Then its last line is `release: gate passed` [check: uvx --from "git+https://homeserver.tailee01ab.ts.net:3000/bolandeu/cli-generator.git@v1.25.0#subdirectory=gate" rb-release check]

## How to test

Seam 2, the CLI under --json through CliRunner (the invoke helpers of tests/test_cli.py); the workflow file read as YAML (tests/test_ci.py); then the uvx gate on the worktree.

## Basis

cli-generator template v1.25.0: template/src/{{ package_name }}/output/__init__.py (RootGroup, _usage_error), template/src/{{ package_name }}/cli.py (cls=output.RootGroup), template/.gitleaks.toml, template/.gitea/workflows/ci.yml.jinja, template/tests/test_cli.py.jinja (the usage error tests), template/tests/test_ci.py. Read them with: git -C /Users/bolandau/Work/tools/cli-generator show v1.25.0:<path>. The Standard: skills/cli-builder/reference/standard.md of the same tag.

## Read first

- `src/rb_dataio/output/__init__.py`
- `tests/test_scripts.py`
- `.agents/antagor/antagor.toml`
- `tests/test_auth.py`
- `scripts/check_command_docstrings.py`

## Out of scope

- copier update and any edit of .copier-answers.yml (_commit stays v1.15.0)
- .github/dependabot.yml, and the Recommended rules the gate does not check
- tests/contracts/schema.json and tests/test_contracts.py: their comments that name release.py stay
- scripts/deploy.sh and the install line of README.md

## Feedback

### Attempt 1: file docstring

- add a docstring to src/rb_dataio/output/__init__.py: what it holds and why

### Blocked: environment_broken (checks ['uv run pytest tests/test_cli.py tests/test_ci.py tests/test_scripts.py'])

The task check ran a subset of tests under the coverage floor (fail_under = 90): it was red on main and on the branch for that reason only. The Architect changed it to --no-cov; the work stays as it is.
