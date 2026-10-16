---
id: DATAIO-012
title: 'SQLite bases: x.sqlite#table read and write with modes, transactions and safe
  concurrent appends'
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
- src/rb_dataio/formats/sqlite.py
- tests/test_sqlite.py
- tests/data/sqlite/
- src/rb_dataio/commands/info.py
- src/rb_dataio/core/dataio/containers.py
- src/rb_dataio/core/dataio/report.py
- src/rb_dataio/core/dataio/pipeline.py
- src/rb_dataio/core/errors.py
- src/rb_dataio/formats/__init__.py
- src/rb_dataio/commands/backups.py
test_paths:
- tests/test_sqlite.py
- tests/data/bases_core/formats/testbase.py
- tests/snapshots/describe.json
- tests/snapshots/help/backups.txt
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
translation: 'SQLite bases (stdlib sqlite3): x.sqlite#t / .db по сигнатуре; таблица
  из адреса или table=, одна — без имени, несколько — список; query внутри базы; замена
  в одной транзакции с копией строк; append: лишняя колонка — WRITE_FAILED, недостающая
  — NULL; сбой посередине — база как была; два процесса append — все строки или понятный
  WRITE_FAILED, база цела; info — таблицы и число строк; formats.'
---

A user reads and writes tables of sqlite files like any other source, through stdlib sqlite3. The format covers .sqlite, .sqlite3 and .db (by the SQLite signature). The table comes from the address fragment or table=; with one table and no name it is read, with several and no name SOURCE_NOT_FOUND lists them. query= runs inside the base. Types map to INTEGER, REAL, TEXT and TIMESTAMP. Every write is one transaction: replace swaps the table (the core keeps the old rows as a backup), append adds rows without changing the schema (an extra column is WRITE_FAILED naming it, a missing column is NULL), and a write that fails midway leaves the base as it was. info lists the tables with their row counts. All the rest (backups, restore, signature routing, query over other sources) comes from the core.

## Acceptance

- Given x.sqlite with table t, When read('x.sqlite#t') runs, Then t is returned; Given one table and no name, Then it is read; Given tables t and u and no name, Then SOURCE_NOT_FOUND lists t and u [check: tests/test_sqlite.py]
- Given a .db file made by stdlib sqlite3, When read, Then this format reads it [check: tests/test_sqlite.py]
- Given query='select * from t where freq > 10' on x.sqlite, When read, Then only those rows are returned and the query ran inside the base [check: tests/test_sqlite.py]
- Given t exists, When write(df, 'x.sqlite#t') replaces it, Then t holds df, backups() has the old rows, and restore brings them back [check: tests/test_sqlite.py]
- Given mode='append' with an extra column, When written, Then WRITE_FAILED names the extra column and t is unchanged; Given a missing column, Then its cells are NULL [check: tests/test_sqlite.py]
- Given a write that fails after half the rows (patched), When it stops, Then t has exactly its old rows [check: tests/test_sqlite.py]
- Given two processes appending 1000 rows each to the same SQLite table at once, When both finish, Then the table has 2000 new rows, or one process got WRITE_FAILED and the table has the other's 1000; the base always passes PRAGMA integrity_check [check: tests/test_sqlite.py]
- Given 'dataio info x.sqlite --json', When it runs, Then the tables are listed with their row counts; Given 'dataio formats --json', Then sqlite is listed with read, write and append [check: tests/test_sqlite.py]

## How to test

Integration tests through the public library API and the CLI under --json on temporary base files created by the tests; concurrency through two subprocesses.

## Basis

The base contract of the core (DATAIO-011) and the container contract (DATAIO-008); stdlib sqlite3; ADR 0002 (a thin wrapper over the engines).

## Read first

- `docs/adr/0002-tonkaya-obertka-nad-dvizhkami.md`
- `CODING_STANDARDS.md`

## Out of scope

- Postgres, MySQL, SQLAlchemy; keys, indexes, upsert; schema migration on append; streaming; the other base format.

## Feedback

### Blocked: scope_held (holders ['DATAIO-009'], paths ['src/rb_dataio/core/dataio/pipeline.py', 'src/rb_dataio/core/errors.py', 'src/rb_dataio/formats/__init__.py'])

DATAIO-009 finished; your kept work on src/rb_dataio/core/dataio/pipeline.py, src/rb_dataio/core/errors.py, src/rb_dataio/formats/__init__.py is back in the worktree; main is merged into your branch where it merges clean

### Attempt 0 (not counted): main moved and conflicts with the work

`main` changed since your work began, and merging it conflicts in:

- `src/rb_dataio/commands/backups.py`
- `tests/snapshots/describe.json`
- `tests/snapshots/help/backups.txt`

Merge it into your branch (`git merge main`), resolve each file keeping both behaviours, `git add` it and run the checks; do not commit: Antagor commits the merge with your work when the round ends (IDEA-201).
