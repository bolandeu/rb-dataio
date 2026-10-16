---
id: DATAIO-023
title: 'Write to an empty remote part: no backup of a part with no columns'
status: in_review
attempts: 0
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
- src/rb_dataio/core/dataio/backup.py
- src/rb_dataio/core/dataio/pipeline.py
- tests/test_remote_core.py
test_paths:
- tests/test_remote_core.py
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
translation: 'Запись в совсем пустой лист Google падает: бэкап пустой части (без колонок)
  в parquet отклоняет DuckDB. Исправить: часть без колонок считать пустой, бэкап не
  делать; тест red → green.'
---

dataio 0.1.20: a write in mode replace with a backup into a completely empty Google Sheets sheet fails with DuckDB 'Need a DataFrame with at least one column'. A sheet with one row or more works. Cause: pipeline.py:237 calls backup.kept_rows on the old rows; kept_rows writes them to parquet through DuckDB, and DuckDB refuses a DataFrame with no columns. An empty part holds nothing to restore.

## Acceptance

- Given a remote sheet with no rows and no columns, When write(frame, url, overwrite=True) runs with a backup, Then the write succeeds, the sheet holds the frame and no backup error is raised [check: tests/test_remote_core.py]
- Given a remote sheet with one row, When the same write runs, Then a backup is kept as before [check: tests/test_remote_core.py]

## How to test

Unit level through the public write() with the FakeSheets fixture of tests/test_remote_core.py; red first: an empty sheet reproduces the DuckDB error.

## Basis

Keep the fix at the backup seam: a part with no columns is treated as empty (no backup kept, or before = empty). Follow the existing tests near test_the_cli_replaces_with_confirm_and_keeps_a_backup.

## Read first

- `src/rb_dataio/core/dataio/pipeline.py`
- `tests/test_remote_core.py`

## Out of scope

- Changes to parquet.write_file for other callers
- The rbtools Doppler wrapper
