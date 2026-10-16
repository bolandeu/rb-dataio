---
id: DATAIO-011
title: 'Bases and SQL in the core: query= over any source, table writes in one transaction,
  table backups as parquet'
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
- src/rb_dataio/core/
- src/rb_dataio/commands/
- src/rb_dataio/__init__.py
- src/rb_dataio/formats/__init__.py
- tests/test_query.py
- tests/test_bases_core.py
- tests/data/bases_core/
- tests/snapshots/
- tests/test_parity.py
test_paths:
- tests/test_query.py
- tests/test_bases_core.py
- tests/test_parity.py
- tests/test_backup.py
docs: none
tools: []
worker_args: null
class: hard
decision: false
visual: null
depends_on:
- DATAIO-008
- DATAIO-009
- DATAIO-010
- DATAIO-021
budget_usd: null
epic: E-003
spec_refs: []
checks:
- python3 scripts/check_command_docstrings.py
- uv run scripts/release.py --check
resident: null
tool: null
pr: null
translation: 'Базы и SQL в ядре: новый параметр query= в read/convert/info и флаг
  CLI (паритет); над базой SQL идёт внутри неё, над любым другим источником — таблица
  data в DuckDB в памяти, над csv/parquet DuckDB читает файл сам; ошибка SQL — READ_FAILED
  с текстом базы. Запись в базу: адаптер пишет таблицу в одной транзакции без копии
  файла; копия — только старые строки таблицы в parquet, restore возвращает их. Определение
  формата по сигнатуре (.db — SQLite или DuckDB). Проверка — тестовым форматом-базой.'
---

Tools filter tables with SQL and keep results in database files. This task adds what every base format and every source needs from the core, so the SQLite and DuckDB formats only implement the base itself.

query=: a new parameter of read, convert (for the source side) and info, with the matching CLI flag (the parity test covers it). Over a base format the adapter runs the SQL inside the base. Over any other source the read frame is the table 'data' in an in-memory DuckDB. Over a csv or parquet file DuckDB reads the file directly and pandas gets only the result. A SQL error is READ_FAILED with the database message.

Base writes: a container adapter may declare that it writes a part in place in one transaction instead of through a copy of the file; the core then does not copy the whole file, keeps a backup of the old rows of that table only (as parquet in the backup store), and restore puts those rows back into the table. Format detection by content: an adapter may claim a file by its signature, so one extension (.db) can belong to SQLite or DuckDB.

The behaviour is proven with a small base format that lives only in the tests, and with CSV, parquet and Python objects for query=.

## Acceptance

- Given a CSV with phrase,freq and query='select phrase from data where freq > 10', When read, Then only the matching rows and the column phrase are returned [check: tests/test_query.py]
- Given a list of dicts or a DataFrame and query=, When read, Then the query runs over it as the table data [check: tests/test_query.py]
- Given a CSV or parquet file and query=, When read, Then DuckDB reads the file directly (the format adapter's read is not called) and the result is the same as over the read frame [check: tests/test_query.py]
- Given query='select nope from data', When read, Then READ_FAILED is raised and its message contains the DuckDB error text [check: tests/test_query.py]
- Given read, convert and info, When their signatures are compared with the CLI, Then query / --query (convert: --in-query is not needed; the source side is query) exist and the parity test passes [check: tests/test_parity.py]
- Given a test base with tables t and u, When write(df, 'base#t') replaces t, Then the file is not copied, backups() has an entry with the old rows of t only, and restore puts the old rows of t back while u is unchanged [check: tests/test_bases_core.py]
- Given two adapters claiming files by signature and a .db file of the second kind, When read, Then the second adapter reads it; Given a .db file of neither kind, Then FORMAT_UNKNOWN [check: tests/test_bases_core.py]

## How to test

Integration tests through the public library API and the CLI under --json; a base format defined in the tests (for example on stdlib sqlite3 with its own signature) registered like the container test format; CSV, parquet and object sources for query=.

## Basis

The container contract of DATAIO-008 and the backup store of the protection modules; DuckDB from DATAIO-010 (ADR 0003); ADR 0002 (a thin wrapper over the engines).

## Read first

- `docs/SPEC.md`
- `docs/adr/0002-tonkaya-obertka-nad-dvizhkami.md`
- `docs/adr/0005-rezervnaya-kopiya-vmesto-voprosov.md`
- `CODING_STANDARDS.md`

## Out of scope

- The real SQLite and DuckDB formats; Postgres, MySQL, SQLAlchemy; keys, indexes, upsert; schema migration; streaming.
