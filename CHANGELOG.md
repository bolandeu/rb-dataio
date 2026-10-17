# Changelog

All notable changes to this project are documented here. Versions follow
[SemVer](https://semver.org/) (while at `0.x`, a minor bump may break).

The changelog is written by `antagor publish`; don't edit it by hand.

## v0.1.22 — 2026-10-17

### Outside epics

- xlsx write is quadratic in the number of rows (DATAIO-024)

## v0.1.21 — 2026-10-16

### Outside epics

- Write to an empty remote part: no backup of a part with no columns (DATAIO-023)

## v0.1.20 — 2026-10-16

### Outside epics

- Small defects after E-002..E-005: int stays int when stacking, error actions fit the case, RAW '=' text in xlsx, mode=error per part, batch edge cases (DATAIO-022)

## v0.1.19 — 2026-10-16

### E-005 — dataio bulk: merge many files, split one table, batch convert (0.6)

One address merges globs, folders and lists with _source and _sheet; a template in the target address splits by a column or by row count into files or sheets; {stem} converts many files one to one; the batch report and failure handling are the same in the library and the CLI.
Time: 1.6h since the epic was approved

- Batch convert: many files one to one with {stem}, stop or keep going, dry-run and per-file backups (DATAIO-020)

## v0.1.18 — 2026-10-16

### E-005 — dataio bulk: merge many files, split one table, batch convert (0.6)

One address merges globs, folders and lists with _source and _sheet; a template in the target address splits by a column or by row count into files or sheets; {stem} converts many files one to one; the batch report and failure handling are the same in the library and the CLI.
Time: 1.6h since the epic was approved

- Split one table: by a column or by row count into files or sheets, with safe names (DATAIO-019)

## v0.1.17 — 2026-10-16

### E-005 — dataio bulk: merge many files, split one table, batch convert (0.6)

One address merges globs, folders and lists with _source and _sheet; a template in the target address splits by a column or by row count into files or sheets; {stem} converts many files one to one; the batch report and failure handling are the same in the library and the CLI.
Time: 1.6h since the epic was approved

- Merge many sources: globs, folders and lists into one table with _source and _sheet (DATAIO-018)

## v0.1.16 — 2026-10-16

### E-005 — dataio bulk: merge many files, split one table, batch convert (0.6)

One address merges globs, folders and lists with _source and _sheet; a template in the target address splits by a column or by row count into files or sheets; {stem} converts many files one to one; the batch report and failure handling are the same in the library and the CLI.
Time: 1.6h since the epic was approved

- Batch surface in the core: merge/split/batch parameters, the batch report, SCHEMA_MISMATCH, and one module per batch behaviour (DATAIO-017)

## v0.1.15 — 2026-10-16

### E-004 — dataio google-http: Google Sheets and http(s) sources (0.5)

A Google Sheets URL or gsheet://id#Sheet reads and writes like a file; the key is found by the standard order and checked by auth status; a 403 says whom to share with; replacing a non-empty sheet asks first and keeps a backup; http(s) CSV and JSON links read directly.
Time: 1.4h since the epic was approved

- Google Sheets: read and write sheets by URL or gsheet://, RAW values, batches, backoff, backups (DATAIO-015)

## v0.1.14 — 2026-10-16

### E-004 — dataio google-http: Google Sheets and http(s) sources (0.5)

A Google Sheets URL or gsheet://id#Sheet reads and writes like a file; the key is found by the standard order and checked by auth status; a 403 says whom to share with; replacing a non-empty sheet asks first and keeps a backup; http(s) CSV and JSON links read directly.
Time: 1.1h since the epic was approved

- http(s) sources: CSV and JSON links, including Google 'Publish to web', read directly (DATAIO-016)

## v0.1.13 — 2026-10-16

### E-004 — dataio google-http: Google Sheets and http(s) sources (0.5)

A Google Sheets URL or gsheet://id#Sheet reads and writes like a file; the key is found by the standard order and checked by auth status; a 403 says whom to share with; replacing a non-empty sheet asks first and keeps a backup; http(s) CSV and JSON links read directly.
Time: 1.1h since the epic was approved

- Remote sources in the core: the Google key and auth status, gsheet and http(s) addresses, start/value_input, confirmation for a non-empty remote part (DATAIO-014)

## v0.1.12 — 2026-10-16

### E-003 — dataio databases-query: SQLite, DuckDB and SQL over any source (0.4)

x.sqlite#table and x.duckdb#table read and write like files, with modes in one transaction and backups; query= runs SQL inside a base or over any source as the table 'data', directly over csv/parquet files for large ones.
Time: 0.7h since the epic was approved

- DuckDB bases: x.duckdb#table read and write with modes and transactions (DATAIO-013)

## v0.1.11 — 2026-10-16

### E-003 — dataio databases-query: SQLite, DuckDB and SQL over any source (0.4)

x.sqlite#table and x.duckdb#table read and write like files, with modes in one transaction and backups; query= runs SQL inside a base or over any source as the table 'data', directly over csv/parquet files for large ones.
Time: 0.6h since the epic was approved

- SQLite bases: x.sqlite#table read and write with modes, transactions and safe concurrent appends (DATAIO-012)

## v0.1.10 — 2026-10-16

### E-003 — dataio databases-query: SQLite, DuckDB and SQL over any source (0.4)

x.sqlite#table and x.duckdb#table read and write like files, with modes in one transaction and backups; query= runs SQL inside a base or over any source as the table 'data', directly over csv/parquet files for large ones.
Time: 0.6h since the epic was approved

- Bases and SQL in the core: query= over any source, table writes in one transaction, table backups as parquet (DATAIO-011)

## v0.1.9 — 2026-10-16

### E-002 — dataio excel-parquet: Excel books and Parquet files (0.3)

read/write/convert/info handle Excel and Parquet like CSV: book.xlsx#Sheet, all sheets at once with _sheet, one sheet replaced while the others stay, a usable xlsx (autowidth, frozen header, autofilter), Parquet without pyarrow.
Time: 0.6h since the epic was approved

- Excel books: read xlsx/xls/xlsb/ods, write xlsx sheets with a usable layout (DATAIO-009)

## v0.1.8 — 2026-10-16

### E-002 — dataio excel-parquet: Excel books and Parquet files (0.3)

read/write/convert/info handle Excel and Parquet like CSV: book.xlsx#Sheet, all sheets at once with _sheet, one sheet replaced while the others stay, a usable xlsx (autowidth, frozen header, autofilter), Parquet without pyarrow.
Time: 0.2h since the epic was approved

- Containers in the core: files with named parts (sheets, tables), reading one or all, writing one part and keeping the rest (DATAIO-008)

## v0.1.7 — 2026-10-16

### E-002 — dataio excel-parquet: Excel books and Parquet files (0.3)

read/write/convert/info handle Excel and Parquet like CSV: book.xlsx#Sheet, all sheets at once with _sheet, one sheet replaced while the others stay, a usable xlsx (autowidth, frozen header, autofilter), Parquet without pyarrow.
Time: 0.1h since the epic was approved

- Parquet files through DuckDB, without pyarrow (DATAIO-010)

## v0.1.6 — 2026-10-16

### Outside epics

- Release installs the new tag on this Mac (DATAIO-007)

## v0.1.5 — 2026-10-16

### E-001 — dataio core: the connector and its contract (0.2)

The library has read/write/convert/info/formats/backups/restore and the CLI has the same capabilities (convert, info, formats, backups, restore). Python objects, txt, csv, tsv, json, jsonl and stdin/stdout work; encoding and delimiter are detected and shown in the report; every error has a code and an action; every replace keeps a backup that restore brings back.
Time: 1.8h since the epic was approved

- Loss warnings come back for --no-backup; old backup entries stay restorable (DATAIO-006)

## v0.1.4 — 2026-10-16

### E-001 — dataio core: the connector and its contract (0.2)

The library has read/write/convert/info/formats/backups/restore and the CLI has the same capabilities (convert, info, formats, backups, restore). Python objects, txt, csv, tsv, json, jsonl and stdin/stdout work; encoding and delimiter are detected and shown in the report; every error has a code and an action; every replace keeps a backup that restore brings back.
Time: 1.7h since the epic was approved

- Backup safety fixes: content file name, no hard links, size check before parsing (DATAIO-005)

## v0.1.3 — 2026-10-16

### E-001 — dataio core: the connector and its contract (0.2)

The library has read/write/convert/info/formats/backups/restore and the CLI has the same capabilities (convert, info, formats, backups, restore). Python objects, txt, csv, tsv, json, jsonl and stdin/stdout work; encoding and delimiter are detected and shown in the report; every error has a code and an action; every replace keeps a backup that restore brings back.
Time: 1.6h since the epic was approved

- Formats and values: CSV/TSV/txt with detection and normalisation, Python objects, JSON/jsonl and stdin/stdout (DATAIO-002)

## v0.1.2 — 2026-10-16

### E-001 — dataio core: the connector and its contract (0.2)

The library has read/write/convert/info/formats/backups/restore and the CLI has the same capabilities (convert, info, formats, backups, restore). Python objects, txt, csv, tsv, json, jsonl and stdin/stdout work; encoding and delimiter are detected and shown in the report; every error has a code and an action; every replace keeps a backup that restore brings back.
Time: 1.3h since the epic was approved

- Protection: backups, restore, atomic writes, write modes, safety checks and loss warnings (DATAIO-004)

## v0.1.1 — 2026-10-16

### E-001 — dataio core: the connector and its contract (0.2)

The library has read/write/convert/info/formats/backups/restore and the CLI has the same capabilities (convert, info, formats, backups, restore). Python objects, txt, csv, tsv, json, jsonl and stdin/stdout work; encoding and delimiter are detected and shown in the report; every error has a code and an action; every replace keeps a backup that restore brings back.
Time: 1h since the epic was approved

- Core frame: read/write/convert/info/formats through the address, the format registry and the report, with the full CLI surface (DATAIO-001)
