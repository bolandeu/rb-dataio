---
id: DATAIO-025
title: An int column with an empty cell reads as float from json, jsonl and Excel
  books
status: done
attempts: 2
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
- tests/test_scripts.py
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

## Feedback

### Attempt 1: checks failed

- `uv run pytest -q` (exit 1)

```
4, 61, 111-112, 159
src/rb_dataio/core/errors.py              126      4    97%   151, 208, 220, 235
src/rb_dataio/core/opencli.py             143     22    85%   108, 112, 141-142, 175, 177, 190-191, 203-238, 256-266
src/rb_dataio/core/version.py              40      7    82%   34-35, 52-53, 57, 64-65
src/rb_dataio/credentials/health.py       105      3    97%   61, 64, 181
src/rb_dataio/credentials/manager.py      146     11    92%   71-72, 81-82, 262, 269-270, 277-280
src/rb_dataio/formats/__init__.py         137     14    90%   57, 134, 137, 141, 148, 163, 166, 193, 196, 199, 220, 224, 241, 259
src/rb_dataio/formats/csv.py               90      3    97%   89, 92-93
src/rb_dataio/formats/duckdb.py            99      3    97%   36, 54, 57
src/rb_dataio/formats/gsheet.py           126      1    99%   88
src/rb_dataio/formats/http.py              41      1    98%   37
src/rb_dataio/formats/json.py              41      3    93%   37, 52, 70
src/rb_dataio/formats/sqlite.py            95      3    97%   41, 129-130
src/rb_dataio/output/__init__.py           94      3    97%   81, 122, 156
src/rb_dataio/output/human.py              18      4    78%   29-32
src/rb_dataio/providers/__init__.py         9      1    89%   28
src/rb_dataio/providers/base.py            61      2    97%   95, 126
src/rb_dataio/providers/google.py          82      8    90%   59-61, 99-100, 132-134
src/rb_dataio/providers/http.py            69      1    99%   34
---------------------------------------------------------------------
TOTAL                                    3425    146    96%

39 files skipped due to complete coverage.
Required test coverage of 90.0% reached. Total coverage: 95.74%
--------------------------- snapshot report summary ----------------------------
20 snapshots passed.
=========================== short test summary info ============================
FAILED tests/test_scripts.py::test_antagor_project_config - AssertionError: a...
1 failed, 646 passed, 1 warning in 13.86s
```

### Attempt 2: the Architect's verdict

Two changes, then done. 1) src/rb_dataio/formats/json.py imports nested_to_record from pandas.io.json._normalize, a private pandas module; pyproject allows any pandas>=3.0, so a minor pandas release can break the import. Use the public API: pd.json_normalize(rows) for the column names and the flattening, then rebuild the cells as Python objects (for example pd.json_normalize(rows).astype(object) where a value is NaN only because pandas made it so), or write a small own flattener of nested dicts into 'a.b' keys (about 10 lines) in json.py. Keep the current tests green. 2) tests/test_scripts.py line 202: do not pin the whole .gitignore list; Antagor adds entries on upgrade. Use: assert {"state/", "receipts/"} <= set((root / ".agents" / "antagor" / ".gitignore").read_text().split()), with a comment above it: Antagor owns this file and may add entries on upgrade.
