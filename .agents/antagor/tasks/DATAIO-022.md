---
id: DATAIO-022
title: 'Small defects after E-002..E-005: int stays int when stacking, error actions
  fit the case, RAW ''='' text in xlsx, mode=error per part, batch edge cases'
status: in_review
attempts: 1
blocked: false
blocked_reason: null
phase: null
tests_hash: null
publish_stage: null
created_by: architect
approved_by: architect
worker: claude-code
type: bugfix
owns_paths:
- src/rb_dataio/core/errors.py
- src/rb_dataio/core/dataio/containers.py
- src/rb_dataio/core/dataio/sources.py
- src/rb_dataio/core/dataio/pipeline.py
- src/rb_dataio/core/dataio/batch.py
- src/rb_dataio/core/dataio/targets.py
- src/rb_dataio/core/dataio/query.py
- src/rb_dataio/core/dataio/values.py
- src/rb_dataio/formats/xlsx.py
- src/rb_dataio/formats/sqlite.py
- src/rb_dataio/formats/duckdb.py
- src/rb_dataio/formats/http.py
- src/rb_dataio/providers/http.py
- src/rb_dataio/commands/convert.py
- tests/test_defects.py
- src/rb_dataio/commands/info.py
- src/rb_dataio/formats/__init__.py
- src/rb_dataio/formats/csv.py
test_paths:
- tests/test_defects.py
- tests/snapshots/describe.json
- tests/snapshots/help/convert.txt
- tests/snapshots/help/info.txt
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
- python3 scripts/check_command_docstrings.py
- uv run scripts/release.py --check
resident: null
tool: null
pr: null
translation: 'Мелкие дефекты после E-002..E-005: int не становится float при склейке;
  подсказки ошибок по делу; текст ''='' в xlsx остаётся текстом; mode=error по таблице/листу,
  а не по файлу; 404 без HTML и без «повторите»; подсказки CLI называют флаги; предупреждения
  пакета не теряются; одинаковые {stem} — ошибка; --split-by без шаблона — ошибка.'
---

Nine small defects found by the Architect in manual checks and by workers (inbox of DATAIO-009, DATAIO-011). Fix each one; add one test per defect in tests/test_defects.py.

## Acceptance

- Given book.xlsx with sheets of different columns and an int column, When read as 'book.xlsx#*', Then the int column stays int (30, not 30.0); Given 'in/*.csv' with different columns, Then the same [check: tests/test_defects.py]
- Given an append that fails on the schema, When it fails, Then the action does not mention the folder of the target [check: tests/test_defects.py]
- Given an SQL error in query=, When read, Then the action speaks of the SQL, not of encoding= or sep= [check: tests/test_defects.py]
- Given a text '=1+1', When written to x.xlsx, Then the cell is the string =1+1, not a formula [check: tests/test_defects.py]
- Given x.sqlite with table t1 (or book.xlsx with Sheet1), When 'x.sqlite#t2' is written with mode error, Then it is written; Given 'x.sqlite#t1', Then TARGET_EXISTS [check: tests/test_defects.py]
- Given an http(s) 404, When read, Then PROVIDER_ERROR has the status and the URL, no response body, and the action does not say to retry [check: tests/test_defects.py]
- Given SCHEMA_MISMATCH or TARGET_EXISTS from the CLI, When shown, Then the action names the CLI flag (drop --strict, --mode replace), not the library argument (strict=False, mode='replace'); the library keeps its own wording [check: tests/test_defects.py]
- Given a batch convert where a file read gives a warning, When it ends, Then the report warnings have it, prefixed by the file [check: tests/test_defects.py]
- Given 'in/**/*.csv' with a/x.csv and b/x.csv and target 'out/{stem}.csv', When converted, Then INVALID_ARGUMENTS names both sources before anything is written [check: tests/test_defects.py]
- Given split_by or chunk_rows and a target without a placeholder, When written, Then INVALID_ARGUMENTS says the target needs {column} or {n} [check: tests/test_defects.py]

## How to test

Unit level through the public API (rb_dataio.read/write/convert) and the CLI under --json via CliRunner; local temp files; the http case with the injected client, no network.

## Basis

Reuse the existing error classes in core/errors.py and their action= argument; follow how DATAIO-008 stacks parts and DATAIO-018 merges sources.

## Read first

- `src/rb_dataio/core/errors.py`
- `src/rb_dataio/core/dataio/pipeline.py`

## Out of scope

- New features, formulas in xlsx, Google Sheets changes, new CLI flags.

## Feedback

### Attempt 1: file docstring

- add a docstring to src/rb_dataio/providers/http.py: what it holds and why
