---
id: DATAIO-018
title: 'Merge many sources: globs, folders and lists into one table with _source and
  _sheet'
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
- src/rb_dataio/core/dataio/sources.py
- tests/test_merge.py
- tests/data/merge/
test_paths:
- tests/test_merge.py
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
translation: 'Слияние многих источников: glob (с **), папка или список адресов → одна
  таблица с _source (source_column=None — без неё), листы книг с _sheet; разные колонки
  — объединение с предупреждением, strict=True — SCHEMA_MISMATCH со списком колонок
  по файлам; пустой glob — SOURCE_NOT_FOUND.'
---

A user reads dozens of same-shaped exports as one table. One address may be a glob (with **), a folder, or a list of addresses; every matched file is read with the usual rules and the tables are stacked with a column naming the file (source_column, default _source; None leaves it out). Sheets of books ('#*') add _sheet as well. Different columns are a union with empty cells and one warning; strict=True raises SCHEMA_MISMATCH listing the columns per file.

## Acceptance

- Given 'in/*.csv' with 3 files, When read, Then one table with a _source column naming each file; Given source_column=None, Then no _source [check: tests/test_merge.py]
- Given 'in/**/*.xlsx' over nested folders, a folder path, and a list of addresses, When read, Then all files are merged the same way [check: tests/test_merge.py]
- Given 'reports/*.xlsx#*' with 2 books of 2 sheets, When read, Then 4 sheets are merged with _source and _sheet [check: tests/test_merge.py]
- Given files with columns (a, b) and (a, c), When read, Then columns a, b, c with empty cells and one warning; Given strict=True, Then SCHEMA_MISMATCH (exit 2 in the CLI) lists both files with their columns [check: tests/test_merge.py]
- Given a glob that matches nothing, When read, Then SOURCE_NOT_FOUND names the pattern [check: tests/test_merge.py]

## How to test

Integration tests through the public library API and the CLI under --json on folders of small CSV and xlsx files written by the tests.

## Basis

The sources seam of DATAIO-017; the container '#*' stacking of DATAIO-008; the xlsx format of DATAIO-009 for the book cases.

## Read first

- `CODING_STANDARDS.md`

## Out of scope

- Splitting; batch convert; joins by key; parallel reads.
