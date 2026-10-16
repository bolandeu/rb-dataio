---
id: DATAIO-002
title: 'Formats and values: CSV/TSV/txt with detection and normalisation, Python objects,
  JSON/jsonl and stdin/stdout'
status: in_progress
attempts: 0
blocked: true
blocked_reason: scope_held
phase: null
tests_hash: null
publish_stage: null
created_by: architect
approved_by: human
worker: claude-code
type: feature
owns_paths:
- src/rb_dataio/formats/
- src/rb_dataio/core/dataio/
- src/rb_dataio/commands/convert.py
- tests/test_csv.py
- tests/test_values.py
- tests/test_objects.py
- tests/test_json.py
- tests/test_stdio.py
- tests/data/csv/
- tests/data/json/
- tests/test_frame.py
- tests/test_cli_frame.py
- tests/snapshots/
test_paths:
- tests/test_csv.py
- tests/test_values.py
- tests/test_objects.py
- tests/test_json.py
- tests/test_stdio.py
- tests/test_frame.py
- tests/test_cli_frame.py
docs: none
tools: []
worker_args: null
class: hard
decision: false
visual: null
depends_on:
- DATAIO-001
- DATAIO-004
budget_usd: null
epic: E-001
spec_refs: []
checks:
- python3 scripts/check_command_docstrings.py
- uv run scripts/release.py --check
resident: null
tool: null
pr: null
translation: 'Форматы и значения: CSV/TSV/txt с определением кодировки и разделителя
  и нормализацией значений, объекты Python, JSON/jsonl и stdin/stdout.


  Слиты бывшие DATAIO-002 и DATAIO-003: обе правят одни файлы ядра, вместе быстрее,
  чем по очереди.


  Приёмка: все пункты обеих задач — cp1251/'';'', BOM, tsv, ''|'', профиль excel,
  append, txt, NA-слова, ведущие нули, as_text/dtypes, починка шапки; строки и объекты
  Python, write без цели, JSON/jsonl, вложенные a.b, кириллица и даты, битый JSON,
  stdin по содержимому, stdout, --json с data.'
---

A user reads CSV files from Excel and 1C without options: cp1251 or UTF-8 with BOM, ';' or tab or '|', and gets correct Cyrillic. The report names what was detected. txt files and phrase lists become one column 'text'. Values keep their meaning: 'NA' and friends stay strings, leading zeros and long IDs stay text, empty rows are dropped. Writing CSV for Excel is one option.

This task fills the value-normalisation step of the read pipeline (it applies to every format) and extends the CSV adapter; it adds txt and tsv adapters.

A tool author passes in-memory data and gets in-memory data back with the same API: a list of strings, a list of dicts, a dict, a Series, a DataFrame, a multi-line string. write(df) with no target returns records, a list, a dict, text, CSV or JSON text. JSON and jsonl files are read and written; nested objects become a.b columns. A user pipes data through stdin and stdout; under --json the data rides inside the envelope so stdout stays one JSON document.

This task fills the value-normalisation step of the read pipeline (it applies to every format), extends the CSV adapter, adds the txt, tsv, objects, json and jsonl adapters, and the stdin/stdout handling of the '-' address. It merges the former CSV/values and objects/JSON tasks because both change the same core files.

## Acceptance

- Given a cp1251 CSV with ';' and Cyrillic, When read, Then the text is correct; When convert or info runs, Then the report has encoding 'cp1251' and delimiter ';' [check: tests/test_csv.py]
- Given a UTF-8-BOM CSV, When dataio processes it, Then the first column name has no BOM; Given encoding='cp1251' or sep='|' passed, Then they are used instead of detection [check: tests/test_csv.py]
- Given a .tsv file, When dataio processes it, Then it is read with tab without sniffing; Given a '|' CSV, Then '|' is detected [check: tests/test_csv.py]
- Given write(df, 'out.csv'), When dataio processes it, Then the file is UTF-8 without BOM with ',' and '\n'; Given profile='excel', Then UTF-8-BOM with ';' [check: tests/test_csv.py]
- Given mode='append' to a CSV with the same header, When dataio processes it, Then rows are added below; Given another header, Then WRITE_FAILED is raised naming both headers and the file is unchanged [check: tests/test_csv.py]
- Given a txt file with lines 'a', '', 'b', When read, Then one column 'text' with rows 'a','b'; When a one-column frame is written to .txt, Then one value per line [check: tests/test_csv.py]
- Given cells 'NA', 'null', 'nan', 'None', '-', When dataio processes it, Then they stay strings; Given an empty cell, Then it is missing and is written back as an empty cell [check: tests/test_values.py]
- Given a column with '007' or '+79001234567' or '1234567890123456', When dataio processes it, Then it stays text; Given '1','2','3', Then it is an integer column; Given ISO dates, Then a date column [check: tests/test_values.py]
- Given as_text=True, When dataio processes it, Then every column is str; Given dtypes={'freq': 'int'}, Then freq is int; Given a value that cannot convert, Then READ_FAILED names the column and the value [check: tests/test_values.py]
- Given header names '', 'phrase', 'phrase', When read, Then columns are col1, phrase, phrase_2 and the report has one warning naming the repairs; Given header=False, Then columns are col1..colN [check: tests/test_values.py]
- Given rows where every cell is empty, When dataio processes it, Then they are dropped [check: tests/test_values.py]
- Given a binary or undecodable file with .csv, When dataio processes it, Then READ_FAILED names the address and the cause [check: tests/test_csv.py]
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

Integration tests through the public library API (read, write, convert, info) on fixture files: cp1251 with ';', UTF-8-BOM with ',', tab, '|', headerless, empty and duplicate header names, NA words, leading zeros, 16-digit IDs, blank lines. Integration tests through the public library API, and CLI tests under --json through CliRunner with input on stdin. Data: inline Python objects and small JSON/jsonl fixtures with nested objects and lists, Cyrillic and dates.

## Basis

Extend the CSV adapter of the frame task; add txt and tsv as new modules of the formats package (the registry finds them). pandas read_csv with keep_default_na=False and na_values=[''] for the NA rule; csv.Sniffer limited to , ; tab | on the first 64 KB. Report fields encoding and delimiter come from the adapter. New modules of the formats package (objects, json, jsonl) plus the stdin/stdout handling of the '-' address; the registry and pipelines of the frame task route to them. pandas json_normalize for nested objects. The envelope comes from output.emit_success.

## Read first

- `docs/SPEC.md`
- `docs/adr/0001-biblioteka-i-cli-ravny.md`
- `docs/adr/0004-stroka-vsegda-adres.md`
- `CONTEXT.md`
- `CODING_STANDARDS.md`

## Out of scope

- Backups, atomic writes and write modes other than CSV append (protection task)
- Excel cell types (Excel epic)
- Any change to the public API or CLI flags (the frame owns them)
