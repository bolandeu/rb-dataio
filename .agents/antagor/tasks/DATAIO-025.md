---
id: DATAIO-025
title: An int column with an empty cell reads as float from json, jsonl and Excel
  books
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
type: bugfix
owns_paths:
- src/rb_dataio/formats/__init__.py
- src/rb_dataio/formats/_excel.py
- src/rb_dataio/formats/json.py
- src/rb_dataio/formats/jsonl.py
- src/rb_dataio/core/dataio/values.py
- tests/test_json.py
- tests/test_excel.py
- tests/test_values.py
test_paths:
- tests/test_json.py
- tests/test_excel.py
- tests/test_values.py
docs: none
tools: []
worker_args: null
class: standard
decision: false
visual: null
depends_on:
- DATAIO-024
budget_usd: null
epic: null
spec_refs: []
checks:
- uv run pytest -q
resident: null
tool: null
pr: null
translation: Чтение json/jsonl/Excel превращает целую колонку с пустой ячейкой во
  float (5 → 5.0). Сделать Int64 с <NA>, как у csv; настоящие float не трогать.
---

Reading json, jsonl or an Excel book (xlsx, xls, xlsb, ods) turns a column of whole numbers with an empty cell into float64: 5, (empty) comes back 5.0, NaN. csv and parquet give Int64 with <NA>. semkit shows 5.0 in every output (IDEA-231). Repro: `printf '{"phrase":"a","freq":5}\n{"phrase":"b","freq":null}\n' > n.jsonl`, then `rb_dataio.read('n.jsonl').dtypes` gives freq float64; expected Int64. The cause is pandas: a column of Python ints with None becomes float64 when the frame is built (`from_cells` for books, the json/jsonl read). Make a column whose present values are all ints (in the source) Int64 with <NA>, as csv does. A column with a real float stays float64. Keep `as_text` and `dtypes` working as now.

## Acceptance

- Given a jsonl with freq 5 and null, When it is read, Then freq is Int64 with values 5 and <NA> [check: tests/test_json.py]
- Given a json array with the same rows, When it is read, Then freq is Int64 [check: tests/test_json.py]
- Given an xlsx with an int column and an empty cell, When it is read, Then the column is Int64 [check: tests/test_excel.py]
- Given a column of 1.5 and null, When it is read from jsonl, Then it stays float64 [check: tests/test_json.py]

## How to test

Unit level through rb_dataio.read on small files in tmp_path, one test per format: json, jsonl, xlsx; ods and xlsb if a fixture exists in tests/data.

## Basis

csv gives Int64 through values.py inference; reuse the Int64 rule of values.py (stack keeps ints as Int64) rather than a new one. Decide at the frame build, where the source types are still known.

## Read first

- `src/rb_dataio/core/dataio/values.py`
- `src/rb_dataio/formats/__init__.py`

## Out of scope

- Write side; csv and parquet (they already keep Int64); the xlsx write speed.
