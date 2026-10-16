---
id: DATAIO-009
title: 'Excel books: read xlsx/xls/xlsb/ods, write xlsx sheets with a usable layout'
status: in_review
attempts: 2
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
- src/rb_dataio/formats/xlsx.py
- src/rb_dataio/formats/xls.py
- src/rb_dataio/formats/xlsb.py
- src/rb_dataio/formats/ods.py
- src/rb_dataio/formats/_excel.py
- tests/test_excel.py
- tests/data/excel/
- pyproject.toml
- src/rb_dataio/core/dataio/pipeline.py
- src/rb_dataio/core/errors.py
- src/rb_dataio/formats/__init__.py
- src/rb_dataio/formats/csv.py
- uv.lock
- src/rb_dataio/core/dataio/settings.py
- src/rb_dataio/data/settings.toml
test_paths:
- tests/test_excel.py
docs: none
tools: []
worker_args: null
class: hard
decision: false
visual: null
depends_on:
- DATAIO-008
budget_usd: null
epic: E-002
spec_refs: []
checks:
- python3 scripts/check_command_docstrings.py
- uv run scripts/release.py --check
resident: null
tool: null
pr: null
translation: 'Книги Excel: чтение xlsx/xls/xlsb/ods через python-calamine с типами
  и правилом ведущих нулей; запись только xlsx (openpyxl): замена одного листа с сохранением
  остальных, Sheet1 по умолчанию, автоширина, закреплённая шапка, автофильтр; append
  с проверкой шапки; > 1 048 576 строк — WRITE_FAILED до записи; предупреждение о
  графиках и сводных; запись xls/xlsb/ods — FORMAT_UNSUPPORTED. Поведение листов (адрес,
  первый, нет листа, #*, info, копии) — из ядра DATAIO-008.'
---

A user reads any Excel book like a CSV and writes xlsx without breaking the rest of the book.

Reading: xlsx, xls, xlsb and ods are each a format (a container of sheets) read through python-calamine; cell types are kept and the leading-zero and long-ID rules of value normalisation apply. Writing: only xlsx is writable (openpyxl); writing one sheet loads the existing book, replaces that sheet and keeps the others; a new book or a book written with no sheet in the address gets the sheet Sheet1; every written sheet has autowidth columns, a frozen header row and an autofilter; append adds rows below the existing ones after checking the header; more than 1 048 576 rows is refused before anything is written; a book with charts or pivot tables warns that they may be lost. Writing xls, xlsb or ods is refused, naming xlsx as the writable Excel format. All the container behaviour (sheet from the address, first sheet, missing sheet, '#*', info parts, backups) comes from the core.

## Acceptance

- Given book.xlsx with sheets A and B, When read('book.xlsx#B') runs, Then sheet B is returned; Given no sheet, Then sheet A; Given sheet 'C', Then SOURCE_NOT_FOUND lists A and B [check: tests/test_excel.py]
- Given .xls, .xlsb and .ods books with a column of '007' and a column of numbers, When read, Then the first sheet is returned, '007' stays text and the numbers are numeric [check: tests/test_excel.py]
- Given book.xlsx with sheets A and B, When write(df, 'book.xlsx#B') runs, Then B holds df, A keeps its values, and backups() has an entry for book.xlsx [check: tests/test_excel.py]
- Given write(df, 'new.xlsx'), When the file is opened with openpyxl, Then the sheet is Sheet1, the header row is frozen (freeze_panes 'A2'), it has an autofilter over the data, and each column width fits its longest value [check: tests/test_excel.py]
- Given a book with a chart or a pivot table, When a sheet is replaced, Then the report warns that charts or pivot tables may be lost [check: tests/test_excel.py]
- Given a frame of 1 048 577 rows, When written to xlsx, Then WRITE_FAILED is raised with the action to use csv or parquet and the target does not exist [check: tests/test_excel.py]
- Given a target .xls, .xlsb or .ods, When written, Then FORMAT_UNSUPPORTED is raised naming xlsx [check: tests/test_excel.py]
- Given mode='append' to book.xlsx#A with the same header, When written, Then the rows go below the old ones; Given another header, Then WRITE_FAILED names both headers and the book is unchanged [check: tests/test_excel.py]
- Given 'dataio info book.xlsx --json', When it runs, Then parts are ['A', 'B']; Given 'dataio formats --json', Then xlsx (read, write, append) and xls, xlsb, ods (read only) are listed [check: tests/test_excel.py]

## How to test

Integration tests through the public library API and the CLI under --json on small fixture books built by the tests with openpyxl (xlsx) and kept as tiny binary fixtures (xls, xlsb, ods); the row limit is checked without building a million-row frame in memory if the adapter allows it (patch the limit).

## Basis

The container contract of the core (DATAIO-008); python-calamine for reading, openpyxl for writing; the CSV adapter shows how an adapter returns Loaded.

## Read first

- `docs/SPEC.md`
- `CONTEXT.md`
- `CODING_STANDARDS.md`

## Out of scope

- Styling beyond autowidth, frozen header and autofilter; writing xls/xlsb/ods; formulas (values only); streaming of large books; Parquet.

## Feedback

### Attempt 1: the Architect's verdict

The review found blockers; close each:

- [blocker] C11 src/rb_dataio/formats/_excel.py: the change adds new readers and a writer, but no error of the Excel libraries reaches the core error handling. `python_calamine.CalamineError` (base of `ZipError`) is not a `ValueError` or `OSError`, so `pipeline.py:67` and `:230` do not catch it. Checked: `read('bad.xlsx')` and `write(df, 'bad.xlsx')` on a file with the text "junk" raise a raw `ZipError`, not `READ_FAILED` or `WRITE_FAILED`. The CLI shows a traceback. `zipfile.BadZipFile` from `_losable` and openpyxl `InvalidFileException` have the same path. The adapter must convert them to `ValueError` (or the core must catch them), with a test.
- [blocker] [wrong] A corrupt or non-book file with an Excel extension gives a raw library exception, not a stable error code — «Errors have a stable code and a next action, in the library and in the CLI alike» (docs/SPEC.md:14). See the C11 remark above.

Minor remarks of the review: optional, if they do not widen the task:

- [minor] C7 src/rb_dataio/formats/xlsx.py: `MAX_ROWS`, `MAX_WIDTH`, `PADDING` are literals in code. `MAX_ROWS` and `MAX_WIDTH` are fixed Excel limits, so this is a judgement call; `PADDING` is a tunable layout value.
- [minor] C5 src/rb_dataio/formats/xlsx.py: xlsx imports the header check from `csv.py` (`require_same_header`) and `plain` from `json.py`. One adapter depends on two others (Shotgun Surgery risk). A shared helper module would be cleaner.
- [minor] C1 src/rb_dataio/formats/_excel.py: `EMPTY_CELL`/`_value` are clear. No `_Avoid_` word found. No other C1 remark.
- [minor] [wrong] Append to an existing but empty sheet: `sheet[1]` gives `[None]` as the header, so the append fails with a header mismatch instead of adding the rows — «Given mode='append' to book.xlsx#A with the same header, When written, Then the rows go below the old ones». Edge case, not in the acceptance list.
- [minor] [wrong] `_value` turns every whole float into `int`, so a float cell `1e20` becomes a huge Python int. Edge case. Not covered by a test.

### Attempt 2: file docstring

- update the docstring of src/rb_dataio/core/dataio/settings.py: +XlsxLayout
