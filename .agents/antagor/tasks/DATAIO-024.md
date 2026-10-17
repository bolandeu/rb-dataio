---
id: DATAIO-024
title: xlsx write is quadratic in the number of rows
status: done
attempts: 1
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
- uv run pytest -q tests/test_excel.py --no-cov
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

## Feedback

### Attempt 1: checks failed

- `uv run pytest -q tests/test_excel.py` (exit 1)

```
90     51    43%   34-40, 45-47, 52-55, 75-83, 86-98, 101-102, 105-114, 117-118, 122-124, 128
src/rb_dataio/formats/duckdb.py              99     60    39%   31, 35-43, 49-57, 62-69, 73-77, 81, 85-86, 90-91, 95-98, 102-105, 117-119, 122-123, 126-127, 130-131, 134-135, 138-145
src/rb_dataio/formats/gsheet.py             126     76    40%   46-49, 52, 55, 58, 62, 72-76, 81-82, 86-89, 94-96, 100, 105-108, 112-115, 123-126, 139-146, 149, 152-154, 157-181, 188-192
src/rb_dataio/formats/http.py                41     16    61%   37, 41-42, 47-52, 56-58, 68-76
src/rb_dataio/formats/json.py                41     19    54%   29, 34-39, 43, 47-49, 53, 62-67, 70
src/rb_dataio/formats/jsonl.py               23     10    57%   20-28, 31
src/rb_dataio/formats/parquet.py             25      8    68%   22-23, 27-29, 38, 41, 44
src/rb_dataio/formats/sqlite.py              95     59    38%   31, 37-41, 46-53, 57-58, 63, 67-73, 78-83, 87-89, 103-104, 107-108, 111-112, 118-124, 127-130, 133-148
src/rb_dataio/formats/txt.py                 30     10    67%   21-22, 32, 35-37, 40-44
src/rb_dataio/output/__init__.py             94     36    62%   79-82, 91, 99-100, 112-123, 130-132, 155-156, 170-175, 199-204, 224
src/rb_dataio/output/human.py                18      9    50%   14, 19, 23-25, 29-32
src/rb_dataio/providers/__init__.py           9      3    67%   27-29
src/rb_dataio/providers/base.py              61     22    64%   93-97, 104-106, 111, 126, 131-144
src/rb_dataio/providers/google.py            82     45    45%   43-44, 54, 59-61, 66, 77, 81-84, 87-92, 96-100, 108-117, 121-134, 142-144
src/rb_dataio/providers/http.py              69     42    39%   30-34, 68, 72-73, 82-111, 118-122, 125-129, 132-136
-----------------------------------------------------------------------
TOTAL                                      3414   1510    56%

17 files skipped due to complete coverage.
FAIL Required test coverage of 90.0% not reached. Total coverage: 55.77%
39 passed in 2.48s
```

### Architect's note

Attempt 1 failed only on the coverage gate: the check ran one test file, and the project needs 90% of the whole package. The check is now 'uv run pytest -q tests/test_excel.py --no-cov'. Your tests passed (39 passed); do not add tests for coverage.

### Answer to question #1

> Check 'uv run pytest -q tests/test_excel.py' fails only on the global coverage gate fail_under=90 (pyproject.toml addopts --cov): one test file covers 56% of src, all 39 tests pass.
> Question: How must the task check pass?
> Options:
> 1. Change the task check to 'uv run pytest -q --no-cov tests/test_excel.py'
> 2. Lower fail_under in pyproject.toml (forbidden by its comment)
> 3. Accept the check as it is; the full suite at publish enforces coverage
> Recommended: Change the task check to 'uv run pytest -q --no-cov tests/test_excel.py'

Option 1 is done: the task check is now 'uv run pytest -q tests/test_excel.py --no-cov'. Do not change pyproject.toml.

### Blocked: needs_scope (entries [{'n': 1, 'text': "Check 'uv run pytest -q tests/test_excel.py' fails only on the global coverage gate fail_under=90 (pyproject.toml addopts --cov): one test file covers 56% of src, all 39 tests pass.\nQuestion: How must"}])
