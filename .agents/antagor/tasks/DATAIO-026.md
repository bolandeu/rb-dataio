---
id: DATAIO-026
title: 'Target columns in write(): select, order, rename for every single target'
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
- src/rb_dataio/core/dataio/options.py
- src/rb_dataio/core/dataio/pipeline.py
- src/rb_dataio/core/dataio/api.py
- src/rb_dataio/core/dataio/columns.py
- src/rb_dataio/core/dataio/__init__.py
- src/rb_dataio/__init__.py
test_paths:
- tests/test_target_columns.py
docs: none
tools: []
worker_args: null
class: standard
decision: false
visual: null
depends_on: []
budget_usd: null
epic: E-006
spec_refs: []
checks:
- python3 scripts/check_command_docstrings.py
- uv run scripts/release.py --check
resident: null
tool: null
pr: null
translation: 'Колонки цели в write(): выбор, порядок, переименование для одиночной
  цели (ядро).


  write() и convert() принимают необязательные columns (исходные имена по порядку)
  и rename (старое → новое). Один шаг формирования: сначала выбор, потом переименование;
  одинаково для csv, xlsx, json, jsonl, parquet, stdout и форматов в памяти. Неверные
  имена и конфликты — InvalidArguments (exit 2) до бэкапа, временного файла и удалённых
  вызовов. Без параметров вывод прежний. Шаблоны (split_by), пакетный convert и Google
  Таблицы — в соседнем блоке.


  Приёмка: выбор и порядок; переименование; сначала выбор, потом rename; неизвестное
  имя — exit 2 со списком колонок, цель не создана; rename отсутствующей или отброшенной
  колонки — exit 2; конфликт — exit 2, обмен a↔b разрешён; append сверяет итоговые
  колонки; итоговые имена в отчёте; records; xlsx, json, parquet, stdout; convert
  одного файла; без параметров вывод прежний.'
---

write() and convert() take two optional arguments: columns (an ordered list of source column names to keep) and rename (a mapping old name -> new name). One shaping step makes the target table: first select by columns, then rename. Every single target gets the same shaped table: csv, xlsx, json, jsonl, parquet, stdout and the in-memory formats (records and the others). Wrong names and clashes are refused with InvalidArguments (exit 2) before any backup, temporary file or remote call. Without both arguments the output is unchanged. This task is the core: templates (split_by, chunk_rows), batch convert and Google Sheets come in a block beside it.

## Acceptance

- Given a table a,b,c, When write(df, 'out.csv', columns=['c','a']), Then out.csv has the header c,a with the values of c and a. [check: tests/test_target_columns.py]
- Given a table a,b, When write(df, 'out.jsonl', rename={'b':'x'}), Then each record has the keys a, x in that order. [check: tests/test_target_columns.py]
- Given columns=['b','a'] and rename={'b':'x'}, When write runs, Then the target columns are x,a (columns names source columns; selection before rename). [check: tests/test_target_columns.py]
- Given columns=['a','zz'] on a table a,b, When write runs, Then InvalidArguments (exit 2) names zz and lists a, b, and no target file exists afterwards. [check: tests/test_target_columns.py]
- Given rename={'zz':'x'}, or rename={'b':'x'} with columns=['a'], When write runs, Then InvalidArguments (exit 2) names the column and lists the columns there are; nothing is written. [check: tests/test_target_columns.py]
- Given rename={'a':'x','b':'x'} or rename={'a':'b'} with b kept, When write runs, Then InvalidArguments (exit 2) names the clashing names; rename={'a':'b','b':'a'} is accepted and swaps the names. [check: tests/test_target_columns.py]
- Given an existing out.csv with header x,a, When write(df, 'out.csv', mode='append', columns=['b','a'], rename={'b':'x'}), Then the rows are appended; with a header that differs, the existing append header check refuses it as before. [check: tests/test_target_columns.py]
- Given columns and rename, When the report is returned, Then report columns are the target names (x,a in the example above). [check: tests/test_target_columns.py]
- Given a table a,b, When write(df, format='records', columns=['a'], rename={'a':'x'}), Then the returned records hold only the key x. [check: tests/test_target_columns.py]
- Given xlsx, json, parquet and stdout targets, When write with columns=['b','a'] and rename={'b':'x'}, Then each target has the columns x,a in that order. [check: tests/test_target_columns.py]
- Given one CSV source, When convert('in.csv', 'out.json', columns=[...], rename={...}), Then out.json has the shaped columns. [check: tests/test_target_columns.py]
- Given no columns and no rename, When write runs to csv and records, Then the output equals the output of the same call without these arguments (all columns, source order and names). [check: tests/test_target_columns.py]

## How to test

Integration tests through the public API rb_dataio.write() and convert() on small DataFrames in tmp_path; error cases assert the error code, exit code 2 and the message text.

## Basis

Follow the WriteOptions validation pattern in options.py and raise InvalidArguments from core errors. Put the validation and the shaping in a new module columns.py with one public function each; call them in one place of the write path that the format adapters, stdout and frame_data share.

## Read first

- `src/rb_dataio/core/dataio/options.py`
- `src/rb_dataio/core/dataio/pipeline.py`
- `src/rb_dataio/core/dataio/api.py`

## Out of scope

- Templates (split_by, chunk_rows), batch convert and Google Sheets (the block beside); the CLI flags, describe and docs (the CLI block); columns or rename on read; pattern or position selection; computed columns.
