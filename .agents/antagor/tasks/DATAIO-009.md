---
id: DATAIO-009
title: 'Excel books: read xlsx/xls/xlsb/ods, write xlsx sheets with a usable layout'
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
- src/rb_dataio/formats/xlsx.py
- src/rb_dataio/formats/xls.py
- src/rb_dataio/formats/xlsb.py
- src/rb_dataio/formats/ods.py
- src/rb_dataio/formats/_excel.py
- tests/test_excel.py
- tests/data/excel/
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
