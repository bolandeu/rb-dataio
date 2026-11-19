# Spec: dataio v1

Source: `docs/brief.md` (interview 2026-10-16, blocks A–M), plan `docs/plans/dataio-v1.md`, idea IDEA-210.
Brief item numbers are given in brackets, e.g. (b14).

## Problem Statement

Every tool of the Human (semkit, serp, wordstat, bukvarix, ad-hoc scripts) needs to read a table from somewhere and save it somewhere else: a CSV in cp1251 with `;`, an Excel book, a Google Sheet, a JSON dump, a SQLite file, a plain list of phrases. Each tool writes these functions again, each with its own bugs: lost leading zeros, «NA» turned into empty, broken Cyrillic in Excel, overwritten sheets. An agent that calls these tools gets a different interface, different errors and different output in each one. A mistake overwrites data with no way back.

## Solution

One package, `dataio` (dist `rb-dataio`, import `rb_dataio`, command `dataio`), that is a connector: it reads any supported source into a `pandas.DataFrame` and writes a DataFrame to any supported target. The library and the CLI have the same capabilities (b2): every option of `read()` / `write()` / `convert()` is a CLI flag with the same name.

A source or target is one address string (`book.xlsx#Sheet1`, `data.duckdb#phrases`, `-`, a Google Sheets URL). dataio detects the format, the encoding and the delimiter itself, and reports every guess. Errors have a stable code and a next action, in the library and in the CLI alike. Before it overwrites anything, dataio keeps a backup, and `restore` brings the old data back.

The CLI follows the shared cli-builder standard: JSON envelope, exit codes, `--dry-run`, `--confirm`, `describe --json`, bundled SKILL.md.

## User Stories

### Reading
1. As a tool author, I want `read("phrases.csv")` to return a DataFrame, so that I stop writing CSV code in every tool.
2. As a user, I want a CSV in cp1251 with `;` read correctly without options, so that files from Excel and 1C just work (b9).
3. As a user, I want to force `encoding` and `sep`, so that I can fix a wrong guess (b9).
4. As an agent, I want the detected encoding and delimiter in the report, so that I can see and correct a guess (b28).
5. As a user, I want `.tsv` always read with tab, so that tab files never get sniffed wrong (b9).
6. As a user, I want a txt file read into one column `text`, one row per line, so that phrase lists become tables (b8).
7. As a user, I want empty rows and empty lines skipped, so that trailing blank lines do not become data (b7).
8. As a tool author, I want to pass a list of strings, a list of dicts, a dict, a Series or a DataFrame, so that in-memory data uses the same API (b8).
9. As a tool author, I want `{col: [values]}` to become columns and `{key: value}` to become `key`, `value` columns, so that both dict shapes are useful (b8).
10. As a user, I want a string with a line break treated as text, so that I can pass pasted content directly (b4).
11. As a user, I want a one-line string always treated as an address, and a missing file to fail with `SOURCE_NOT_FOUND`, so that a typo in a file name never becomes silent text (b4).
12. As a user, I want `format="text"` to force a string to be text, so that I can read a single word as data (b4).
13. As a user, I want JSON arrays of records, objects of columns and jsonl read, so that any common JSON dump works (b12).
14. As a user, I want nested JSON objects flattened into `a.b` columns, and nested lists kept as JSON strings, so that API dumps become flat tables (b12).
15. As a user, I want to read from stdin with the format detected from the content, so that I can pipe data in (b14).
16. As a user, I want `--limit N`, so that I or an agent can peek at a large source (b23).
17. As a user, I want `header=False` to name columns `col1, col2, …`, so that headerless CSV works (b8).
18. As a user, I want empty and duplicate header names repaired (`col3`, `phrase_2`) with a warning, so that every column has a unique name (b8).

### Types and values
19. As a user, I want «NA», «null», «nan», «None», «-» kept as strings, so that real words are never lost (b7).
20. As a user, I want an empty cell read as a missing value and written as an empty cell, so that missing data round-trips (b7).
21. As a user, I want numbers and dates detected, so that I can compute on them (b7).
22. As a user, I want a column kept as text when any value has a leading zero, a leading `+` or more than 15 digits, so that IDs and phones are never damaged (b7).
23. As a user, I want `as_text=True`, so that everything is read as strings when I need exact values (b7).
24. As a user, I want `dtypes={"freq": "int"}` / `--dtype freq=int`, so that I can fix one column's type (b7).
25. As a user, I want Excel cell types taken as they are, with the same leading-zero rule, so that Excel data keeps its meaning (b7).

### Writing
26. As a tool author, I want `write(df, "out.csv")` to return a report with target, format, mode, rows and columns, so that I can log what happened (b21).
27. As a tool author, I want `write(df, format="records")` with no target to return the data as an object (`records`, `list`, `dict`, `text`, `csv`, `json`), so that I can convert in memory (b21).
28. As a user, I want CSV written as UTF-8 with `,` by default, so that other tools read it (b10).
29. As a user, I want `profile="excel"` to write UTF-8-BOM with `;`, so that Excel opens Cyrillic correctly (b10).
30. As a user, I want JSON written as records with real Cyrillic and ISO dates, and jsonl one record per line, so that files are readable (b12).
31. As a user, I want stdout to get CSV by default and plain text for a single column, so that pipes are simple (b14).
32. As an agent, I want `--json` with target `-` to put the data inside the envelope as `data`, so that stdout stays one JSON document (b14).
33. As a user, I want `mode=replace|append|error` on every target, so that one word means the same everywhere (b20, b37).
34. As a user, I want `replace` to replace only the named sheet or table and keep the rest of the file, so that a book or base is not lost (b20).
35. As a user, I want writes to be atomic (temporary file, then rename), so that a crash never leaves a broken file (b20).
36. As a user, I want `append` to add rows to csv/jsonl/txt, to an xlsx sheet, and to json/parquet by rewrite, so that I can grow a dataset (b20).
37. As a user, I want `append` to a CSV with a different header to fail, so that columns never shift (b20).
37a. As a tool author, I want `write(df, t, columns=[...], rename={...})` and `dataio convert --columns --rename` to give every target the chosen target columns under the new names (selection first, then rename), so that semkit saves `phrase,similarity` as `phrase,score` (refused with `INVALID_ARGUMENTS`, exit 2, on a wrong name or a clash).

### Address and parameters
38. As a user, I want one address string for both source and target, so that I learn one syntax (b3).
39. As a user, I want to paste a Google Sheets browser URL and get the sheet from its `gid`, so that I do not copy IDs by hand (b3).
40. As a user, I want every address part available as a parameter (`sheet`, `table`, `format`), with the parameter winning, so that names with `#` still work (b3).
41. As a tool author, I want the same parameter names in every format and in the CLI (`as_text` ↔ `--as-text`), so that nothing has to be looked up twice (b36, b37).
42. As a user, I want `convert` to take `in_`/`out_` prefixes for options that both sides have, so that `--in-encoding cp1251 --out-encoding utf-8` is clear (b38).

### Errors and reports
43. As a tool author, I want every failure raised as `DataioError` with `code`, `message` and `action`, so that I catch one type (b26).
44. As an agent, I want the CLI to return the standard error envelope and exit code, so that I handle dataio like every other tool (b26).
45. As an agent, I want `message` to name the address and the cause, and `action` to name the fix (for example the list of existing sheets), so that I can recover alone (b27).
46. As an agent, I want `info` to return format, rows, columns with types, a 5-row preview and the list of sheets or tables, so that I can explore a source before I convert it (b29).
47. As an agent, I want `formats` to list every format, what it can read and write, and its options, so that I discover capabilities without docs (b35).
48. As an agent, I want `--dry-run` to return the same report without writing, so that I can check a plan (b28).

### Protection
49. As a user, I want a backup before every replace of an existing file, sheet, table or Google sheet, so that I can undo a mistake (b40).
50. As a user, I want `dataio backups` and `dataio restore [ID]` (and `backups()`, `restore(id)`), so that undo is one command (b41).
51. As a user, I want `restore` to back up the current state first, so that an undo can be undone (b41).
52. As a user, I want backups limited (50 operations, 14 days, 2 GB, objects over 500 MB skipped with a warning), so that they do not fill the disk (b40).
53. As a user, I want `--no-backup`, so that I can skip backups for throwaway outputs (b40).
54. As a user, I want writing over the source itself to need `overwrite=True` / `--confirm`, so that `convert a.csv a.csv --query …` cannot destroy data by accident (b42).
55. As an agent, I want a warning when the row count drops sharply or columns disappear, so that I notice a bad overwrite and restore it (b43).
56. As an agent, I want `--dry-run` to show `exists`, `rows_before`, `rows_after` per target, so that I see what will be replaced (b44).

### Excel and Parquet
57. As a user, I want xlsx, xls, xlsb and ods read, so that any book opens (b2, b11).
58. As a user, I want `book.xlsx#*` to read all sheets with a `_sheet` column, so that a book becomes one table (b6).
59. As a user, I want xlsx written with autowidth, a frozen header and an autofilter, so that the file is usable at once (b11).
60. As a user, I want a warning when the book has charts or pivots that may be lost, so that I am not surprised (b11).
61. As a user, I want writing more than 1 048 576 rows to fail with an action to use csv or parquet, so that data is not cut (b11).
62. As a user, I want writing xls/xlsb/ods to fail with `FORMAT_UNSUPPORTED`, so that the limits are clear (b11).
63. As a user, I want parquet read and written without pyarrow, so that installs stay light (b13).

### Databases and queries
64. As a user, I want `x.sqlite#t` and `x.duckdb#t` to read and write a table, so that bases work like files (b15).
65. As a user, I want `.db` files detected as SQLite or DuckDB from the file signature, so that the extension does not matter (b15).
66. As a user, I want a base with one table read without naming it, and a base with many to fail with the list, so that the common case is short (b15).
67. As a user, I want `query=` to run inside the base, so that I read only what I need (b15).
68. As a user, I want `query=` over any source with the table called `data`, so that I can filter a CSV with SQL (b3).
69. As a user, I want `query=` over csv/parquet run by DuckDB on the file directly, so that large files can be filtered without loading them (b22).
70. As a user, I want base writes in one transaction, so that a failure leaves the base as it was (b15).
71. As a user, I want `append` with extra columns to fail and missing columns to become NULL, so that the schema never changes silently (b15).

### Google Sheets and http
72. As a user, I want the service account key found from `--credentials`, `DATAIO_GOOGLE_*`, the keychain or `GOOGLE_APPLICATION_CREDENTIALS`, so that it works on any machine (b45).
73. As a user, I want `dataio auth status --check` to show where the key came from, whether it works, and the service account email, so that I know whom to share a sheet with (b16).
74. As a user, I want a 403 to fail with «Share the sheet with <email> as Editor», so that I fix access in one step (b16).
75. As a user, I want a missing sheet created, `start="A5"` honoured, and values written RAW, so that `007` stays `007` and `=…` is not a formula (b17).
76. As a user, I want `replace` to clear values but keep the sheet's formatting, so that my layout stays (b17).
77. As a user, I want replacing a non-empty sheet to ask for confirmation in the CLI and to need `overwrite=True` in the library, so that a remote sheet is never wiped by accident (b18).
78. As a user, I want writes in batches of 10 000 rows with retries on 429/5xx, and a clear error above the 10M-cell limit, so that large sheets work (b19).
79. As a user, I want http(s) URLs (including «Publish to web» links) read, so that remote CSVs need no download step (b5).

### Bulk operations
80. As a user, I want `'in/*.csv'`, `'in/**/*.xlsx'`, a folder or a list of addresses merged into one table with `_source`, so that I can combine exports (b30).
81. As a user, I want `'reports/*.xlsx#*'` to read all sheets of all books, so that one command collects everything (b30).
82. As a user, I want different columns merged as a union with a warning, and `strict=True` to fail with `SCHEMA_MISMATCH` and the columns per file, so that I choose between tolerant and exact (b30).
83. As a user, I want `split_by="region"` with `out/{region}.csv` or `book.xlsx#{region}`, so that one table becomes many files or sheets (b31).
84. As a user, I want `chunk_rows=10000` with `out/part_{n}.csv`, so that a large table becomes parts (b31).
85. As a user, I want `convert 'in/*.csv' 'out/{stem}.xlsx'` to convert each file on its own, so that batch conversion is one command (b32).
86. As an agent, I want a batch report with `targets`, stop on the first error by default, and `keep_going` to collect `errors`, so that I control failure handling (b33).

### Standard and integration
87. As an agent, I want `describe --json`, `--ai` and the bundled SKILL.md, so that I learn dataio like every other tool (b49, b50).
88. As a tool author, I want a test that fails when a library parameter and a CLI flag diverge, so that parity holds (b39).
89. As the semkit maintainer, I want to put a consumer contract into dataio's tests, so that a dataio release cannot break semkit (b51).
90. As a user, I want project defaults (for example `csv.profile = "excel"`) in `.rb_dataio/config.toml`, but no project needed to run, so that dataio works anywhere (b49).

## Implementation Decisions

- **Layers** follow the cli-builder contract: commands only map flags to one service call; all logic lives in the core; external services sit behind providers; credentials go through the template's credential manager.
- **Public API** (one module, the package root): `read(source, **opts) -> DataFrame`, `write(df, target=None, **opts) -> Report | object` (typed with overloads), `convert(source, target, **opts) -> Report`, `info(source, **opts) -> Info`, `formats() -> list[FormatInfo]`, `backups() -> list[Backup]`, `restore(id=None) -> Report`. The CLI command `convert` calls `convert()`; `read` from the CLI is `convert SRC -`.
- **Parameter vocabulary** (single source, shared by library and CLI): `format`, `sheet`, `table`, `query`, `encoding`, `sep`, `header`, `as_text`, `dtypes`, `limit`, `mode`, `start`, `profile`, `split_by`, `chunk_rows`, `drop_split_column`, `source_column`, `strict`, `keep_going`, `overwrite`, `backup`, `credentials`, `value_input`, `columns`, `rename`. Flag = name with `_` → `-`; booleans `--flag` / `--no-flag`; dicts as a repeatable `key=value` flag. In `convert`, options both sides have take `in_` / `out_`.
- **Address module**: parses an address string into a structured address (scheme, path or id, fragment = sheet or table, template placeholders `{column}`, `{n}`, `{stem}`, glob). Explicit parameters override parsed parts. Recognised: local paths by extension, `-`, `gsheet://<id>`, Google Sheets URLs (with `gid`), `http(s)://`, globs and folders.
- **Format registry**: each format is one adapter with `read` and/or `write`, its own option set and its capabilities; `formats()` is generated from the registry. Engines: pandas for text formats; `python-calamine` for Excel read; `openpyxl` for xlsx write; DuckDB for parquet and for `query=`; stdlib `sqlite3`; `gspread` for Google Sheets.
- **Detection**: format by scheme, then extension, then content (stdin, `.db` signature). CSV encoding chain `utf-8-sig` → `utf-8` → `cp1251`; delimiter sniffed on the first 64 KB among `, ; \t |`.
- **Value normalisation** is one shared step after every read: NA words kept, empty → missing, type inference with the leading-zero / 15-digit rule, `as_text`, `dtypes`, empty-row removal, header repair.
- **Write pipeline**: resolve target → dry-run short-circuit → safety checks (target equals source, non-empty Google sheet) → backup → atomic write → report with warnings (row drop, lost columns).
- **Report contract** (CLI success envelope and library return value share it): `source {uri, format, encoding, delimiter, rows, columns}`, `target {uri, format, mode, rows}` or `targets [{uri, rows}]` for batches, `warnings [...]`, `errors [{uri, code, message}]` for `keep_going`, dry-run fields `exists`, `rows_before`, `rows_after`.
- **Errors**: `DataioError` is a subclass of the template's `CliError`. New codes: `SOURCE_NOT_FOUND` (exit 2), `FORMAT_UNKNOWN` (2), `FORMAT_UNSUPPORTED` (2), `SCHEMA_MISMATCH` (2), `TARGET_EXISTS` (1), `READ_FAILED` (1), `WRITE_FAILED` (1). Standard codes reused: `AUTH_REQUIRED` (3), `PROVIDER_ERROR` (5), `ABORTED`, `INVALID_ARGUMENTS`. No new exit codes.
- **Backup store**: in the user data dir (platformdirs), declared in the template's data-files list so `describe --json` shows it. One entry per operation: id, time, target, rows, and the old content (the original file, or parquet for sheets and tables). Retention: 50 entries, 14 days, 2 GB; objects over 500 MB skipped with a warning.
- **Google provider** `google`: service-account field bag; resolution order flag → `DATAIO_GOOGLE_*` → keychain → `GOOGLE_APPLICATION_CREDENTIALS` as the legacy env name; `health_check()` is one cheap authorised call; gspread errors map to `AuthRequired` / `ProviderError`; 403 adds the share hint with the service account email. Writes RAW, batches of 10 000 rows, retry with backoff on 429/5xx, 10M-cell limit checked before writing.
- **http provider** on the template's `HttpProvider` (retries, timeouts, error mapping).
- **Confirmation**: `convert` (replacing a non-empty Google sheet, writing over the source) and `restore` use the template's `require_confirmation`; both support `--dry-run`; SKILL.md lists them as destructive. The library uses `overwrite=True` instead of a prompt.
- **CLI surface**: `convert`, `info`, `formats`, `backups`, `restore` next to the template's `status`, `doctor`, `auth`, `config`, `describe`, `skill`; the template's placeholder `run` is removed. dataio works without a project; the project config only holds defaults.
- **No streaming in v1**: data is loaded whole; `query=` over csv/parquet is the large-file path.
- **Delivery order** (each a release): core → excel-parquet → databases-query → google-http → bulk (`docs/plans/dataio-v1.md`).

## Testing Decisions

- A good test checks behaviour seen from outside: what `read()` returns, what file `write()` leaves, what report and error come back. It never asserts on private helpers, engine calls or internal structures, so engines can change without test changes.
- TDD: the failing test is committed first; existing tests are never edited to fit the code; the gate is `gate check` (the command is in `AGENTS.md`).
- **Seam 1, the public library API** (`read`, `write`, `convert`, `info`, `formats`, `backups`, `restore`): almost all behaviour — formats, detection, types, modes, errors with codes and actions, backups and restore, bulk. Real temporary files; fixtures for cp1251/`;` CSV, BOM, leading zeros, NA words, nested JSON, multi-sheet books, SQLite/DuckDB files.
- **Seam 2, the CLI under `--json`** through `CliRunner`: envelope shape, exit codes, `--dry-run`, `--confirm` / `--non-interactive`, stdout data rules, and the parity test between function signatures and CLI flags. The template's existing help snapshots, `describe` snapshot and `auth status` shape tests stay and cover the new commands.
- **Seam 3, consumer contracts** (`tests/contracts/`): offline and keyless; the existing tools-catalog contract is prior art; semkit adds its own.
- Google and http are tested through an injected client or transport (as `HttpProvider` tests already do in the template), never the network.
- Prior art in the repo: the template's `test_cli.py`, `test_help.py`, `test_describe.py`, `test_auth.py`, `test_http_provider.py`, `test_providers.py`, `test_contracts.py`.

## Out of Scope

- S3 and other cloud object stores (b5).
- Postgres, MySQL and SQLAlchemy (later) (b15).
- Streaming reads and writes (later, through DuckDB) (b22).
- Excel styling beyond autowidth, frozen header and autofilter; writing xls, xlsb, ods (b11).
- Creating new Google Spreadsheets (the service account would own them) (b17).
- Primary keys, indexes and upsert in bases (b15).
- Schema changes on `append` (b15).
- Secrets in project config (b45).
- Choosing columns on read (only the target columns are chosen).
- Migrating semkit and other tools to dataio: their own work, after the first release.

## Further Notes

- Under Antagor this spec becomes the epic cards: one card per plan epic, created when the Human says the plan is final (`antagor-epic`), then sliced (`antagor-slice`). The cards take their acceptance from the user stories of their epic.
- Terms: `CONTEXT.md` (Адрес, Источник, Цель, Режим записи, Отчёт, Резервная копия). Decisions with reasons: `docs/adr/0001`–`0005`.
- The project mode is switched to `fast` by the Human: `antagor -C /Users/bolandau/Work/tools/rb-dataio mode set fast`.
