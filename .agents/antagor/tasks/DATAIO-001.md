---
id: DATAIO-001
title: 'Core frame: read/write/convert/info/formats through the address, the format
  registry and the report, with the full CLI surface'
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
type: feature
owns_paths:
- src/rb_dataio/__init__.py
- src/rb_dataio/cli.py
- src/rb_dataio/commands/
- src/rb_dataio/core/errors.py
- src/rb_dataio/core/dataio/
- src/rb_dataio/formats/__init__.py
- src/rb_dataio/formats/csv.py
- pyproject.toml
- tests/test_frame.py
- tests/test_cli_frame.py
- tests/test_parity.py
- tests/test_cli.py
- tests/test_help.py
- tests/snapshots/
- tests/data/frame/
test_paths:
- tests/test_frame.py
- tests/test_cli_frame.py
- tests/test_parity.py
- tests/test_help.py
- tests/test_describe.py
docs: none
tools: []
worker_args: null
class: hard
decision: false
visual: null
depends_on: []
budget_usd: null
epic: E-001
spec_refs: []
checks:
- python3 scripts/check_command_docstrings.py
- uv run scripts/release.py --check
resident: null
tool: null
pr: null
translation: 'Каркас ядра: read/write/convert/info/formats через адрес, реестр форматов
  и отчёт; полная поверхность CLI.


  Тонкий сквозной путь, который расширяют остальные задачи: модель адреса (параметр
  важнее адреса), реестр форматов (новый формат — один новый модуль), конвейеры чтения
  и записи с крючками для нормализации, защиты и копий, контракт отчёта, DataioError
  с кодами dataio, весь словарь параметров ядра в API и во флагах CLI сразу, все пять
  команд (convert, info, formats, backups, restore — последние две заглушками), удаление
  заглушки run, тест паритета. Формат — только минимальный CSV (UTF-8, '','').


  Приёмка: read/write/convert CSV с отчётом; разбор адреса; FORMAT_UNKNOWN и SOURCE_NOT_FOUND
  с действием; конверт --json и коды выхода; info и --limit; formats из реестра; тест
  паритета; help без run; --dry-run ничего не пишет.'
---

The thin end-to-end path of dataio that every later task extends.

A tool author calls read("a.csv") and gets a DataFrame; write(df, "b.csv") writes it and returns a report; convert("a.csv", "b.csv") does both; info("a.csv") describes the source; formats() lists what this release can read and write. The CLI has the same capabilities: `dataio convert SRC DST`, `dataio info SRC`, `dataio formats`, with the standard --json envelope.

This task sets the frame:
- the address model: one string parsed into scheme, path, fragment (sheet or table) and placeholders; explicit parameters override the parsed parts; in this task only local paths are resolved, '-' and other schemes are recognised but may raise FORMAT_UNSUPPORTED until their task;
- the format registry: one adapter per format, found automatically from the formats package (a new format is one new module, no edit of a central list), each with read/write/append ability and its options; formats() and the FORMAT_UNKNOWN list come from it; this task ships only a minimal CSV adapter (UTF-8, ',', header row);
- the read pipeline: resolve address -> adapter read -> one value-normalisation step (a pass-through hook here; the CSV/values task fills it) -> limit;
- the write pipeline: resolve target -> dry-run -> safety checks -> backup -> write -> report (safety, backup and atomic write are hooks here; the protection task fills them);
- the report contract shared by the library and the CLI envelope: source {uri, format, encoding, delimiter, rows, columns}, target {uri, format, mode, rows, columns}, warnings;
- DataioError as a subclass of the template CliError with the codes SOURCE_NOT_FOUND(2), FORMAT_UNKNOWN(2), FORMAT_UNSUPPORTED(2), TARGET_EXISTS(1), READ_FAILED(1), WRITE_FAILED(1); no new exit codes;
- the full v1-core parameter vocabulary already on the API and as CLI flags, so later tasks change behaviour, not the surface: format, sheet, table, encoding, sep, header, as_text, dtypes, limit, mode, profile, overwrite, backup (in convert: in_/out_ for options of both sides). A parameter whose behaviour belongs to a later task is accepted and passed through;
- all five commands registered with their final flags: convert, info, formats, backups, restore; backups and restore may answer FORMAT_UNSUPPORTED-free stubs (an empty list; restore refuses with a clear 'not available yet' CliError) until the protection task;
- the template placeholder command run is removed (command, help snapshot, tests).

## Acceptance

- Given a UTF-8 CSV a.csv with columns phrase,freq and 3 rows, When read('a.csv') is called, Then a DataFrame with those 2 columns and 3 rows is returned [check: tests/test_frame.py]
- Given that DataFrame, When write(df, 'b.csv') is called, Then b.csv has the same content and the result is {target: {uri: 'b.csv', format: 'csv', mode: 'replace', rows: 3, columns: ['phrase','freq']}, warnings: []} [check: tests/test_frame.py]
- Given a.csv, When convert('a.csv', 'b.csv') is called, Then the report has source and target parts with rows 3 [check: tests/test_frame.py]
- Given the address 'book.xlsx#Sheet1' and sheet='Other', When it is parsed, Then the sheet is 'Other' (the parameter wins); Given 'data.duckdb#phrases', Then the fragment is the table [check: tests/test_frame.py]
- Given 'notes.xyz', When read, Then DataioError FORMAT_UNKNOWN is raised, its action lists the known formats, and exit code is 2 in the CLI [check: tests/test_cli_frame.py]
- Given a one-line string that is no existing file, When read, Then SOURCE_NOT_FOUND is raised naming the address, with action "Pass format='text' to read the string as text" [check: tests/test_frame.py]
- Given 'dataio convert a.csv b.csv --json', When dataio processes it, Then stdout is one JSON object {ok: true, source: {...}, target: {...}, warnings: []} and exit 0; Given a missing source, Then {ok: false, error: {code: 'SOURCE_NOT_FOUND', message, action}} and exit 2 [check: tests/test_cli_frame.py]
- Given 'dataio info a.csv --json', When dataio processes it, Then format, rows, columns with types and a preview of at most 5 rows are returned; Given --limit 2 on convert, Then the target has 2 rows [check: tests/test_cli_frame.py]
- Given 'dataio formats --json', When dataio processes it, Then every registered format is listed with read, write, append ability and its options; adding a module to the formats package adds it to the list without other edits [check: tests/test_frame.py]
- Given every keyword parameter of read, write and convert, When dataio processes it, Then the matching CLI command has a flag with the same name (_ -> -, booleans as --x/--no-x, dicts as a repeatable key=value flag), and a missing or extra flag fails the parity test [check: tests/test_parity.py]
- Given 'dataio' with no arguments, When dataio processes it, Then the help lists convert, info, formats, backups, restore next to the template commands and has no run; each new command has an Example line and a help snapshot [check: tests/test_help.py]
- Given 'dataio convert a.csv b.csv --dry-run --json', When dataio processes it, Then the report is returned and b.csv is not created [check: tests/test_cli_frame.py]

## How to test

Integration tests through the public library API on real temporary files, and CLI tests under --json through CliRunner. Data: small UTF-8 CSV files written by the tests. Help and describe snapshots refreshed with uv run pytest --snapshot-update.

## Basis

Follow the template layers: commands only map flags to one core call (output.guard, output.emit_success, JsonOption, DryRunOption). Errors subclass core/errors.py CliError like the existing ones. pandas is the engine; add it as a dependency here. The parity test walks the Typer app like tests/test_help.py does.

## Read first

- `docs/SPEC.md`
- `docs/adr/0001-biblioteka-i-cli-ravny.md`
- `docs/adr/0004-stroka-vsegda-adres.md`
- `CONTEXT.md`
- `CODING_STANDARDS.md`

## Out of scope

- Encoding and delimiter detection, value normalisation, txt and tsv (CSV/values task)
- Python objects, JSON, jsonl, stdin/stdout (objects/JSON task)
- Backups, restore behaviour, atomic writes, append/error modes, safety checks (protection task)
- Excel, parquet, bases, Google, http, bulk (later epics)
