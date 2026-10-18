---
id: DATAIO-027
title: Target columns for templates, batch convert and Google Sheets
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
- src/rb_dataio/core/dataio/targets.py
- src/rb_dataio/core/dataio/batch.py
test_paths:
- tests/test_target_columns_many.py
docs: none
tools: []
worker_args: null
class: standard
decision: false
visual: null
depends_on:
- DATAIO-026
- DATAIO-028
budget_usd: null
epic: E-006
spec_refs: []
checks:
- python3 scripts/check_command_docstrings.py
- uv run scripts/release.py --check
resident: null
tool: null
pr: null
translation: 'Колонки цели для шаблонов, пакетного convert и Google Таблиц.


  columns и rename работают для записи во много целей и в удалённую цель. Шаблон (split_by,
  chunk_rows) делит таблицу по исходным именам, потом каждая часть формируется; имена
  проверяются один раз до первой части. drop_split_column — как если бы колонки разбиения
  не было в columns. Пакетный convert формирует каждый вывод; ошибка имени для одного
  источника подчиняется keep_going. Google Таблица получает выбранные колонки под
  новыми именами.


  Приёмка: split_by без колонки разбиения в columns; с ней и переименованием; drop_split_column
  + rename этой колонки — exit 2; неверное имя — ни одного файла; chunk_rows; пакетный
  convert по маске; keep_going при ошибке одного источника; Google Таблица (фейк)
  — заголовок x,a.'
---

columns and rename from the core work for every write that makes many targets or a remote one. A template target (split_by, chunk_rows) splits the source table by source column names, then each part is shaped; the names are checked once before the first part, so a wrong name writes no part. drop_split_column acts as if the split column were not in columns. A batch convert of several sources shapes each output; a wrong name for one source follows keep_going like any other error of that source. A Google Sheets target gets the chosen columns in order under the new names.

## Acceptance

- Given a table region,a,b and split_by='region', columns=['a'], When write(df, 'out/{region}.csv', ...), Then one file per region value, each with only column a. [check: tests/test_target_columns_many.py]
- Given split_by='region', columns=['region','a'], rename={'region':'r'}, When write runs, Then each file has the header r,a. [check: tests/test_target_columns_many.py]
- Given split_by='region', drop_split_column=True and rename={'region':'r'}, When write runs, Then it is refused with InvalidArguments (exit 2) because region is left out; no file is written. [check: tests/test_target_columns_many.py]
- Given split_by='region' and columns=['a','zz'], When write runs, Then InvalidArguments (exit 2) names zz before any part is written: the out folder holds no file. [check: tests/test_target_columns_many.py]
- Given chunk_rows=2 on 5 rows and columns=['b'], When write(df, 'out/part_{n}.csv', ...), Then three files, each with only column b. [check: tests/test_target_columns_many.py]
- Given three CSV sources in one folder, When convert('in/*.csv', 'out/{stem}.json', columns=['a'], rename={'a':'x'}), Then each output holds only the key x; the batch report lists three targets. [check: tests/test_target_columns_many.py]
- Given two sources where one lacks column a, When convert('in/*.csv', 'out/{stem}.csv', columns=['a']) without keep_going, Then it stops with exit 2 naming a and the source; with keep_going=True the other output is written and the report errors list the failed source. [check: tests/test_target_columns_many.py]
- Given a Google Sheets target through the fake provider of the tests, When write(df, gsheet target, columns=['b','a'], rename={'b':'x'}), Then the sheet gets the header x,a and the matching values. [check: tests/test_target_columns_many.py]

## How to test

Integration tests through the public API write() and convert() in tmp_path; Google Sheets through the fake provider and fixtures the existing gsheet tests use (import them, do not change them).

## Basis

Reuse the validation and shaping functions of the core (DATAIO-026, module columns.py); follow how targets.py and batch.py pass WriteOptions to pipeline.write_frame.

## Read first

- `src/rb_dataio/core/dataio/targets.py`
- `src/rb_dataio/core/dataio/batch.py`
- `tests/test_gsheet.py`

## Out of scope

- The core shaping and validation (DATAIO-026); the CLI flags, describe and docs (the CLI block); read.
