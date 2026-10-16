---
id: DATAIO-020
title: 'Batch convert: many files one to one with {stem}, stop or keep going, dry-run
  and per-file backups'
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
- src/rb_dataio/core/dataio/batch.py
- tests/test_batch_convert.py
- tests/data/batch/
test_paths:
- tests/test_batch_convert.py
docs: none
tools: []
worker_args: null
class: standard
decision: false
visual: null
depends_on:
- DATAIO-017
- DATAIO-009
budget_usd: null
epic: E-005
spec_refs: []
checks:
- python3 scripts/check_command_docstrings.py
- uv run scripts/release.py --check
resident: null
tool: null
pr: null
translation: 'Пакетная конвертация: convert in/*.csv out/{stem}.xlsx — каждый файл
  в свой; по умолчанию стоп на первой ошибке, keep_going=True — остальные делаются,
  errors с кодами и ok false; --dry-run — список целей с exists/rows_before/rows_after
  без записи; у каждого заменённого файла своя копия.'
---

A user converts a folder of files in one command. convert with a many-source address and a target template with {stem} converts each source to its own target. By default the run stops at the first error; keep_going=True does the rest and the report has errors [{uri, code, message}] with ok false. --dry-run lists every target with exists, rows_before and rows_after and writes nothing. Each replaced file has its own backup.

## Acceptance

- Given 'dataio convert in/*.csv out/{stem}.xlsx' with a.csv and b.csv, When it runs, Then out/a.xlsx and out/b.xlsx exist with their rows and targets lists both [check: tests/test_batch_convert.py]
- Given three sources where the second is broken, When converted, Then it stops after the first with the error of the second; Given keep_going=True, Then the first and third are written and errors has the second with its code, ok false, exit 1 [check: tests/test_batch_convert.py]
- Given --dry-run on a batch where one target exists, When it runs, Then every target is listed with exists, rows_before and rows_after and nothing is written [check: tests/test_batch_convert.py]
- Given a batch that replaces two existing files, When it ends, Then backups() has one entry per file and restore of each brings its old content back [check: tests/test_batch_convert.py]

## How to test

Integration tests through the public library API and the CLI under --json on folders of small files written by the tests.

## Basis

The batch seam and report of DATAIO-017; the write pipeline and backups; the xlsx format of DATAIO-009.

## Read first

- `CODING_STANDARDS.md`

## Out of scope

- Merging many sources into one table; splitting; parallel processing.
