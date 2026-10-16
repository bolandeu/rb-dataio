---
id: DATAIO-013
title: 'DuckDB bases: x.duckdb#table read and write with modes and transactions'
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
type: feature
owns_paths:
- src/rb_dataio/formats/duckdb.py
- tests/test_duckdb.py
- tests/data/duckdb/
- src/rb_dataio/commands/info.py
- src/rb_dataio/core/dataio/containers.py
- src/rb_dataio/core/dataio/pipeline.py
- src/rb_dataio/core/dataio/report.py
- src/rb_dataio/core/errors.py
- src/rb_dataio/formats/__init__.py
test_paths:
- tests/test_duckdb.py
docs: none
tools: []
worker_args: null
class: standard
decision: false
visual: null
depends_on:
- DATAIO-011
budget_usd: null
epic: E-003
spec_refs: []
checks:
- python3 scripts/check_command_docstrings.py
- uv run scripts/release.py --check
resident: null
tool: null
pr: null
translation: 'DuckDB bases: x.duckdb#t / .db по сигнатуре; таблица из адреса или table=;
  query внутри базы; замена в одной транзакции с копией строк; append: лишняя колонка
  — WRITE_FAILED, недостающая — NULL; сбой посередине — база как была; занятая база
  — понятный WRITE_FAILED; info — таблицы и число строк; formats.'
---

A user reads and writes tables of duckdb files like any other source, through the duckdb package. The format covers .duckdb and .db (by the DuckDB signature). The table comes from the address fragment or table=; with one table and no name it is read, with several and no name SOURCE_NOT_FOUND lists them. query= runs inside the base. Types map to INTEGER, REAL, TEXT and TIMESTAMP. Every write is one transaction: replace swaps the table (the core keeps the old rows as a backup), append adds rows without changing the schema (an extra column is WRITE_FAILED naming it, a missing column is NULL), and a write that fails midway leaves the base as it was. info lists the tables with their row counts. All the rest (backups, restore, signature routing, query over other sources) comes from the core.

## Acceptance

- Given x.duckdb with table t, When read('x.duckdb#t') runs, Then t is returned; Given one table and no name, Then it is read; Given tables t and u and no name, Then SOURCE_NOT_FOUND lists t and u [check: tests/test_duckdb.py]
- Given a .db file made by the duckdb package, When read, Then this format reads it [check: tests/test_duckdb.py]
- Given query='select * from t where freq > 10' on x.duckdb, When read, Then only those rows are returned and the query ran inside the base [check: tests/test_duckdb.py]
- Given t exists, When write(df, 'x.duckdb#t') replaces it, Then t holds df, backups() has the old rows, and restore brings them back [check: tests/test_duckdb.py]
- Given mode='append' with an extra column, When written, Then WRITE_FAILED names the extra column and t is unchanged; Given a missing column, Then its cells are NULL [check: tests/test_duckdb.py]
- Given a write that fails after half the rows (patched), When it stops, Then t has exactly its old rows [check: tests/test_duckdb.py]
- Given an open read of x.duckdb by another connection in the same process, When write runs, Then it either succeeds or raises WRITE_FAILED with the action to close the other connection; the base is never broken [check: tests/test_duckdb.py]
- Given 'dataio info x.duckdb --json', When it runs, Then the tables are listed with their row counts; Given 'dataio formats --json', Then duckdb is listed with read, write and append [check: tests/test_duckdb.py]

## How to test

Integration tests through the public library API and the CLI under --json on temporary base files created by the tests; concurrency through two subprocesses.

## Basis

The base contract of the core (DATAIO-011) and the container contract (DATAIO-008); the duckdb package; ADR 0002 (a thin wrapper over the engines).

## Read first

- `docs/adr/0002-tonkaya-obertka-nad-dvizhkami.md`
- `CODING_STANDARDS.md`

## Out of scope

- Postgres, MySQL, SQLAlchemy; keys, indexes, upsert; schema migration on append; streaming; the other base format.

## Feedback

### Blocked: scope_held (holders ['DATAIO-009', 'DATAIO-012'], paths ['src/rb_dataio/commands/info.py', 'src/rb_dataio/core/dataio/containers.py', 'src/rb_dataio/core/dataio/pipeline.py', 'src/rb_dataio/core/dataio/report.py', 'src/rb_dataio/core/errors.py', 'src/rb_dataio/formats/__init__.py'])

DATAIO-009, DATAIO-012 finished; your kept work on src/rb_dataio/commands/info.py, src/rb_dataio/core/dataio/containers.py, src/rb_dataio/core/dataio/pipeline.py, src/rb_dataio/core/dataio/report.py, src/rb_dataio/core/errors.py, src/rb_dataio/formats/__init__.py is back in the worktree; main is merged into your branch where it merges clean

`main` changed since your work began, and merging it conflicts in:

- `src/rb_dataio/commands/info.py`
- `src/rb_dataio/core/dataio/containers.py`
- `src/rb_dataio/core/dataio/pipeline.py`
- `src/rb_dataio/core/dataio/report.py`
- `src/rb_dataio/core/errors.py`
- `src/rb_dataio/formats/__init__.py`

Merge it into your branch (`git merge main`), resolve each file keeping both behaviours, `git add` it and run the checks; do not commit: Antagor commits the merge with your work when the round ends (IDEA-201).
