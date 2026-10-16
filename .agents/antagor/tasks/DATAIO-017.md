---
id: DATAIO-017
title: 'Batch surface in the core: merge/split/batch parameters, the batch report,
  SCHEMA_MISMATCH, and one module per batch behaviour'
status: publish
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
- tests/test_batch_surface.py
- tests/snapshots/
- tests/test_parity.py
test_paths:
- tests/test_batch_surface.py
- tests/test_parity.py
- tests/test_frame.py
- tests/test_cli_frame.py
docs: none
tools: []
worker_args: null
class: standard
decision: false
visual: null
depends_on:
- DATAIO-008
- DATAIO-011
- DATAIO-014
- DATAIO-015
- DATAIO-016
budget_usd: null
epic: E-005
spec_refs: []
checks:
- python3 scripts/check_command_docstrings.py
- uv run scripts/release.py --check
resident: null
tool: null
pr: null
translation: 'Поверхность пакетной работы в ядре: новые параметры source_column, strict,
  split_by, chunk_rows, drop_split_column, keep_going (+ флаги, паритет); пакетный
  отчёт targets/errors (ok false), в --dry-run — exists/rows_before/rows_after по
  каждой цели; ошибка SCHEMA_MISMATCH (exit 2); по пустому модулю на поведение (sources,
  targets, batch), которые конвейер уже спрашивает. Нынешнее поведение не меняется.
  Дальше три задачи идут параллельно, каждая в своём модуле.'
---

The batch work (merge many sources, split one table, convert many files one to one) needs the same public surface and report in the library and the CLI. This task sets that surface once and leaves one empty module per behaviour, so the three behaviours are built in parallel without touching shared files.

New parameters on the API with CLI flags (the parity test covers them): source_column (default '_source'), strict, split_by, chunk_rows, drop_split_column, keep_going. The batch report: targets [{uri, rows}] for batches, errors [{uri, code, message}] with ok false when any failed, and in --dry-run every target with exists, rows_before and rows_after. A new error SCHEMA_MISMATCH (exit 2) carrying the columns per source. The read pipeline asks the sources module whether an address names many sources (it answers 'no' for now); the write pipeline asks the targets module whether a target is a template (it answers 'no' for now); convert asks the batch module whether it is a many-to-many run (it answers 'no' for now). Today's single-source behaviour stays exactly the same.

## Acceptance

- Given read, write and convert, When compared with the CLI, Then source_column, strict, split_by, chunk_rows, drop_split_column and keep_going exist as flags with the same defaults and the parity test passes [check: tests/test_parity.py]
- Given a report with targets and errors, When it is emitted under --json, Then the envelope has targets [{uri, rows}], errors [{uri, code, message}] and ok false when errors is not empty, exit 1 [check: tests/test_batch_surface.py]
- Given SchemaMismatch with columns per source, When raised in the CLI, Then the code is SCHEMA_MISMATCH, exit 2, and the message lists each source with its columns [check: tests/test_batch_surface.py]
- Given the sources, targets and batch modules patched to claim an address, When read, write or convert runs, Then the pipeline calls them; unpatched, Then every existing frame, CSV, objects and protection test passes unchanged [check: tests/test_batch_surface.py]

## How to test

Integration tests through the public library API and the CLI under --json; the three behaviour modules patched in the tests to prove the seams.

## Basis

The frame's parameter vocabulary, the report contract and the errors module; commands only map flags to one core call.

## Read first

- `docs/SPEC.md`
- `docs/adr/0001-biblioteka-i-cli-ravny.md`
- `CODING_STANDARDS.md`

## Out of scope

- The merge, split and batch-convert behaviours themselves (the next three tasks); parallel processing; joins; streaming.
