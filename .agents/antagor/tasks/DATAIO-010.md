---
id: DATAIO-010
title: Parquet files through DuckDB, without pyarrow
status: in_review
attempts: 0
blocked: false
blocked_reason: null
phase: null
tests_hash: null
publish_stage: null
created_by: architect
approved_by: human
worker: claude-code
type: feature
owns_paths:
- src/rb_dataio/formats/parquet.py
- tests/test_parquet.py
- tests/data/parquet/
- pyproject.toml
- uv.lock
test_paths:
- tests/test_parquet.py
- tests/test_deps.py
docs: none
tools: []
worker_args: null
class: standard
decision: false
visual: null
depends_on: []
budget_usd: null
epic: E-002
spec_refs: []
checks:
- python3 scripts/check_command_docstrings.py
- uv run scripts/release.py --check
resident: null
tool: null
pr: null
translation: 'Parquet через DuckDB без pyarrow: чтение и запись, имена и типы колонок
  туда-обратно (int, float, кириллица, bool, даты, пропуски); ''007'' в строковой
  колонке остаётся строкой; pyarrow не ставится и не импортируется; convert csv↔parquet
  и formats; append — FORMAT_UNSUPPORTED. Независима от ядра контейнеров — идёт параллельно.'
---

A user reads and writes Parquet like any other table. The Parquet format reads and writes through DuckDB (ADR 0003), so pyarrow is never installed. Column names and types round-trip (integers, floats, strings with Cyrillic, booleans, dates and timestamps, missing values). The leading-zero rule does not re-type a Parquet column: its stored type wins. Parquet is not a container and does not append.

## Acceptance

- Given a frame with int, float, str (Cyrillic), bool, date and timestamp columns and a missing value, When write(df, 'a.parquet') and read('a.parquet') run, Then the columns, the values and the dtypes are the same [check: tests/test_parquet.py]
- Given a Parquet string column holding '007', When read, Then it stays the string '007' [check: tests/test_parquet.py]
- Given the installed package, When its dependencies are resolved, Then pyarrow is not among them and importing rb_dataio does not import pyarrow [check: tests/test_parquet.py]
- Given 'dataio convert a.csv a.parquet --json' and back, When it runs, Then exit 0 and the rows match; Given 'dataio formats --json', Then parquet is listed with read and write and without append [check: tests/test_parquet.py]
- Given mode='append' to a.parquet, When written, Then FORMAT_UNSUPPORTED is raised and the file is unchanged [check: tests/test_parquet.py]

## How to test

Integration tests through the public library API and the CLI under --json on temporary files written by the tests; the pyarrow check inspects the installed distribution metadata and sys.modules after import.

## Basis

ADR 0003: DuckDB, no pyarrow; the CSV adapter shows how an adapter reads into Loaded and writes a frame; add duckdb as a dependency here.

## Read first

- `docs/adr/0003-parquet-cherez-duckdb.md`
- `CODING_STANDARDS.md`

## Out of scope

- Excel; SQL queries and DuckDB tables (E-003); partitioned datasets.
