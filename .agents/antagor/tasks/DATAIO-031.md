---
id: DATAIO-031
title: 'Tests pass in Gitea Actions: help and stderr text stay plain under GITHUB_ACTIONS'
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
type: bugfix
owns_paths:
- tests/conftest.py
- tests/test_help.py
- tests/test_cli.py
- tests/test_cli_target_columns.py
test_paths:
- tests/conftest.py
- tests/test_help.py
- tests/test_cli.py
- tests/test_cli_target_columns.py
docs: none
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
- sh -c "GITHUB_ACTIONS=true FORCE_COLOR=1 PY_COLORS=1 uv run pytest --no-cov -q -p
  no:cacheprovider"
- uvx --from "git+https://homeserver.tailee01ab.ts.net:3000/bolandeu/cli-generator.git@v1.25.0#subdirectory=gate"
  rb-release check
resident: null
tool: null
pr: null
translation: 'CI dataio на homeserver красный с v0.1.27: Gitea Actions ставит GITHUB_ACTIONS=true,
  Typer принудительно включает цвет Rich, 21 тест (снимки --help и проверки текста)
  получает ANSI-коды. Как в шаблоне (CG-020): autouse-фикстура в tests/conftest.py
  выключает typer.rich_utils.FORCE_TERMINAL, тесты «то же в CI» прогоняют проблемные
  тесты под переменными CI. Тесты первыми, src/ не меняется.'
---

The CI of dataio on the Gitea runner is red since v0.1.27: 21 tests fail, 662 pass. Log:
https://homeserver.tailee01ab.ts.net:3000/bolandeu/dataio/actions/runs/302/jobs/490/logs (public).

## Cause

Gitea Actions sets `GITHUB_ACTIONS=true`. Typer reads `GITHUB_ACTIONS`, `FORCE_COLOR` and `PY_COLORS` once, at import
(`typer.rich_utils.FORCE_TERMINAL`), and then forces terminal output: Rich colours and ANSI codes. The tests that
compare help text or stderr text then fail:

- `tests/test_help.py::test_help_snapshot` (19 help pages);
- `tests/test_cli.py::test_usage_error_without_json_stays_on_stderr`;
- `tests/test_cli_target_columns.py::test_describe_and_help_show_both_options`.

Repro on the Mac: `GITHUB_ACTIONS=true uv run pytest --no-cov -q` gives the same 21 failures; without the variable
all tests pass. The Python version is not the cause (the gate passes on 3.11 locally).

Template cli-generator fixed the same in CG-020 (after v1.15.0, dataio's template version): `tests/conftest.py`
has `CI_ENV` and the fixture `same_in_ci`, and `tests/test_help.py` has an autouse fixture that sets
`typer.rich_utils.FORCE_TERMINAL` to False, and `test_help_is_the_same_in_ci`.
Read: `git -C /Users/bolandau/Work/tools/cli-generator show v1.25.0:template/tests/conftest.py.jinja` and
`... show v1.25.0:template/tests/test_help.py.jinja`.

## Do

1. Tests first: in `tests/conftest.py` add `CI_ENV` and `same_in_ci` as in the template. Add a test "the same in CI"
   for each of the three failing places: `test_help.py` (selection `test_help_snapshot`), `test_cli.py` (selection
   `test_usage_error_without_json_stays_on_stderr`), `test_cli_target_columns.py` (selection
   `test_describe_and_help_show_both_options`). They must fail before step 2. Put the red run in the report.
2. Fix: one autouse fixture in `tests/conftest.py` that sets `typer.rich_utils.FORCE_TERMINAL` to False (monkeypatch),
   so every test of the suite renders plain text, also under CI. Not one fixture per file.
3. Do not change `src/`: the CLI keeps Typer's behaviour for real users.

## Acceptance

- Given GITHUB_ACTIONS=true, FORCE_COLOR=1 and PY_COLORS=1 in the environment, When the whole test suite runs, Then every test passes [check: sh -c "GITHUB_ACTIONS=true FORCE_COLOR=1 PY_COLORS=1 uv run pytest --no-cov -q -p no:cacheprovider"]
- Given the suite runs without those variables, When the "same in CI" tests run, Then they rerun the help snapshot, usage-error and target-columns help tests under CI_ENV and pass [check: tests/test_help.py]

## How to test

Pytest in a subprocess with CI_ENV (the template's same_in_ci fixture): the only way to set a value Typer reads at import. Then the whole suite with GITHUB_ACTIONS=true.

## Basis

cli-generator template v1.25.0: template/tests/conftest.py.jinja (CI_ENV, same_in_ci) and template/tests/test_help.py.jinja (_plain_help, test_help_is_the_same_in_ci), from task CG-020. Read with: git -C /Users/bolandau/Work/tools/cli-generator show v1.25.0:<path>.

## Read first

- `tests/conftest.py`
- `tests/test_help.py`

## Out of scope

- src/: the CLI keeps Typer's colour behaviour for real users
- the CI workflow and its Python version (stays the lowest supported, 3.11)
- help snapshots: their text does not change
