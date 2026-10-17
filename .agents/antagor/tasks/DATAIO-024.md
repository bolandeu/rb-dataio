---
id: DATAIO-024
title: xlsx write is quadratic in the number of rows
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
type: bugfix
owns_paths:
- src/rb_dataio/formats/xlsx.py
- tests/test_excel.py
test_paths:
- tests/test_excel.py
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
- uv run pytest -q tests/test_excel.py
resident: null
tool: null
pr: null
translation: 'Запись xlsx квадратична по числу строк: openpyxl max_row пересчитывается
  на каждой строке. Сделать запись линейной, поведение (формулы ''='', append, шапка,
  ширины) не менять.'
---

Writing xlsx takes O(n^2) time: 10k rows 3.8 s, 100k rows 326 s, 1M rows does not end in 15 min (semkit e2e, IDEA-231). Reading the same 100k-row xlsx takes 1.3 s. The cause: `_append_row` in src/rb_dataio/formats/xlsx.py calls `sheet[sheet.max_row]` after each `sheet.append`; openpyxl computes `max_row` over all cells at each call. Make the write linear. Keep the rule that a text which starts with `=` stays a string, not a formula. Keep append mode, header, freeze panes, auto filter and column widths as they are now. Check `_lay_out` too: it must stay one pass over the cells.

## Acceptance

- Given a frame of 100k rows (a text column and an int column), When it is written to xlsx, Then the write ends in less than 20 s and the read back gives the same rows [check: tests/test_excel.py]
- Given a text cell '=1+1', When it is written to xlsx, Then it reads back as the string '=1+1' [check: tests/test_excel.py]

## How to test

Unit level through the xlsx adapter or rb_dataio.write. A timing test: 20k rows against 2k rows, the time ratio stays near linear (at most 20x for 10x rows); keep it fast enough for the normal test run.

## Basis

Find the new row from the row index openpyxl gives on append (or check the values for a leading '=' before the append), not from max_row. Follow the style of the module.

## Read first

- `src/rb_dataio/formats/xlsx.py`

## Out of scope

- The write-only openpyxl workbook: append mode needs the loaded book.
- Other formats; the temporary file of a killed write; read-side types.
