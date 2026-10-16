---
id: DATAIO-003
title: Python objects, JSON, jsonl and stdin/stdout, including in-memory write targets
status: cancelled
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
- src/rb_dataio/formats/objects.py
- src/rb_dataio/formats/json.py
- src/rb_dataio/formats/jsonl.py
- src/rb_dataio/core/dataio/stdio.py
- src/rb_dataio/commands/convert.py
- tests/test_objects.py
- tests/test_json.py
- tests/test_stdio.py
- tests/data/json/
- src/rb_dataio/core/dataio/api.py
- src/rb_dataio/core/dataio/pipeline.py
- src/rb_dataio/core/dataio/registry.py
- src/rb_dataio/formats/__init__.py
test_paths:
- tests/test_objects.py
- tests/test_json.py
- tests/test_stdio.py
- tests/snapshots/describe.json
- tests/snapshots/help/convert.txt
- tests/test_frame.py
docs: none
tools: []
worker_args: null
class: standard
decision: false
visual: null
depends_on:
- DATAIO-001
budget_usd: null
epic: E-001
spec_refs: []
checks:
- python3 scripts/check_command_docstrings.py
- uv run scripts/release.py --check
resident: null
tool: null
pr: null
translation: 'Объекты Python, JSON, jsonl и stdin/stdout, включая запись в память.


  Автор инструмента передаёт данные в памяти и получает их обратно тем же API; write(df)
  без цели возвращает records/list/dict/text/csv/json. JSON и jsonl читаются и пишутся,
  вложенное раскладывается в a.b. Данные идут через stdin/stdout; при --json данные
  — внутри конверта.


  Приёмка: строки и многострочный текст → text; list of dict, dict колонок, dict ключ-значение,
  Series; write без цели → объекты; JSON-массив, объект колонок, jsonl — один результат;
  вложенные объекты и списки; запись JSON с кириллицей и ISO-датами, jsonl; битый
  JSON → READ_FAILED; stdin по содержимому; stdout CSV/текст/--format; --json с data.'
---

A tool author passes in-memory data and gets in-memory data back with the same API: a list of strings, a list of dicts, a dict, a Series, a DataFrame, a multi-line string. write(df) with no target returns records, a list, a dict, text, CSV or JSON text. JSON and jsonl files are read and written; nested objects become a.b columns. A user pipes data through stdin and stdout; under --json the data rides inside the envelope so stdout stays one JSON document.

## Acceptance

- Given ['a', 'b'] or the string 'a\nb', When read, Then one column 'text' with rows 'a','b' [check: tests/test_objects.py]
- Given [{'a': 1, 'b': 2}], When dataio processes it, Then columns a, b; Given {'a': [1, 2], 'b': [3, 4]}, Then columns a, b with 2 rows; Given {'x': 1, 'y': 2}, Then columns key, value; Given a Series named 'freq', Then column freq; unnamed, Then column value [check: tests/test_objects.py]
- Given write(df, format='records'), When dataio processes it, Then a list of dicts is returned and nothing is written; Given 'list', Then the first column as a list; 'dict', 'text', 'csv', 'json', Then the matching object or string [check: tests/test_objects.py]
- Given a JSON array of records, an object of columns, and a jsonl file, When read, Then the same DataFrame each time [check: tests/test_json.py]
- Given {'user': {'name': 'Иван'}, 'tags': ['a', 'b']}, When read, Then column user.name is 'Иван' and column tags is the JSON string '["a", "b"]' [check: tests/test_json.py]
- Given write to .json, When dataio processes it, Then records with indent 2, real Cyrillic (no \u escapes) and ISO dates; Given .jsonl, Then one record per line [check: tests/test_json.py]
- Given broken JSON, When dataio processes it, Then READ_FAILED names the address and the line [check: tests/test_json.py]
- Given CSV on stdin, When 'dataio convert - out.json' runs, Then the format is detected from the content; Given '[' or '{' first, Then JSON or jsonl; Given lines with no stable delimiter, Then text [check: tests/test_stdio.py]
- Given 'dataio convert a.csv -', When dataio processes it, Then CSV goes to stdout; Given a one-column frame, Then one value per line; Given --format json, Then JSON [check: tests/test_stdio.py]
- Given 'dataio convert a.csv - --json', When dataio processes it, Then stdout is exactly one JSON object {ok: true, ..., data: [records]} [check: tests/test_stdio.py]

## How to test

Integration tests through the public library API, and CLI tests under --json through CliRunner with input on stdin. Data: inline Python objects and small JSON/jsonl fixtures with nested objects and lists, Cyrillic and dates.

## Basis

New modules of the formats package (objects, json, jsonl) plus the stdin/stdout handling of the '-' address; the registry and pipelines of the frame task route to them. pandas json_normalize for nested objects. The envelope comes from output.emit_success.

## Read first

- `docs/SPEC.md`
- `docs/adr/0001-biblioteka-i-cli-ravny.md`
- `docs/adr/0004-stroka-vsegda-adres.md`
- `CONTEXT.md`
- `CODING_STANDARDS.md`

## Out of scope

- Encoding detection and value normalisation (CSV/values task)
- Backups and write modes (protection task)
- New parameters or flags (the frame owns them)
