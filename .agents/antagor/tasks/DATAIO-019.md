---
id: DATAIO-019
title: 'Split one table: by a column or by row count into files or sheets, with safe
  names'
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
type: feature
owns_paths:
- src/rb_dataio/core/dataio/targets.py
- tests/test_split.py
- tests/data/split/
test_paths:
- tests/test_split.py
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
translation: 'Разбиение одной таблицы: шаблон цели {колонка} с split_by — файл или
  лист на значение, {n} с chunk_rows — нумерованные части; drop_split_column; недопустимые
  символы в именах файлов и листов заменяются (лист ≤ 31 символа), targets показывает
  итоговые имена; каждая запись — через обычный конвейер с копиями.'
---

A user splits one table without a script. A target address may be a template: {column} with split_by writes one file or one sheet per value; {n} with chunk_rows writes numbered parts. drop_split_column=True leaves the split column out. Values with characters not allowed in file or sheet names are replaced, and the report lists the final names in targets. Each written file goes through the normal write pipeline (modes, backups).

## Acceptance

- Given split_by='region' and target 'out/{region}.csv' with regions msk and spb, When written, Then out/msk.csv and out/spb.csv hold their rows; Given drop_split_column=True, Then region is not in the files [check: tests/test_split.py]
- Given 'book.xlsx#{region}', When written, Then one sheet per region in one book [check: tests/test_split.py]
- Given chunk_rows=10000 and 'out/part_{n}.csv' with 25 000 rows, When written, Then part_1, part_2, part_3 with 10 000, 10 000 and 5 000 rows [check: tests/test_split.py]
- Given a region value 'a/b:c*' for a file and a 40-character value for a sheet, When split, Then the names are sanitised (no / : * in files, at most 31 characters and no [ ] : * ? / \ in sheets) and targets lists the final names [check: tests/test_split.py]
- Given a template target that replaces existing files, When written, Then each has its backup and restore works per file [check: tests/test_split.py]

## How to test

Integration tests through the public library API and the CLI under --json on frames built in the tests; xlsx output checked with openpyxl.

## Basis

The targets seam of DATAIO-017; the write pipeline and backups; the xlsx format of DATAIO-009 for sheets.

## Read first

- `CODING_STANDARDS.md`

## Out of scope

- Merging; batch convert ({stem}); joins.
