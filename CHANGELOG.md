# Changelog

All notable changes to this project are documented here. Versions follow
[SemVer](https://semver.org/) (while at `0.x`, a minor bump may break).

The changelog is written by `antagor publish`; don't edit it by hand.

## v0.1.33 — 2026-10-26

### Main

- Merge local main (Antagor config)
- Merge pull request #1: template v1.27.3 (Renovate)
- chore(template): Update dependency https://homeserver.tailee01ab.ts.net:3000/bolandeu/cli-generator.git to v1.27.3
- antagor.toml: mode fast


## v0.1.32 — 2026-10-23

### Outside epics

- Template update v1.15.0 -> v1.27.1: apply the merged patch (DATAIO-040)

## v0.1.31 — 2026-10-21

### Outside epics

- README states the package's own release facts only, not Antagor's process (DATAIO-039)

## v0.1.30 — 2026-10-21

### E-007 — Join: a VLOOKUP-like join of a main source with lookup sources by named key columns

dataio join main.csv out.xlsx --lookup prices.xlsx#Prices --on sku (and join() in the library) writes the main table with the lookup's columns matched by the named keys (left, right, inner or full; one key or several) to any target, with a report of how many rows found a match.
Time: 1.2h since the epic was approved

- join() in the library: a main source and lookups joined by named key columns (DATAIO-035)
- dataio join: the CLI command over join(), with the flags of convert (DATAIO-036)
- Docs of join: the skill and the README show a VLOOKUP-like join by two keys (DATAIO-037)
- join: the repeated-keys warning names only keys that are repeated in the lookup (DATAIO-038)

## v0.1.29 — 2026-10-21

### Outside epics

- Tests pass in Gitea Actions: help and stderr text stay plain under GITHUB_ACTIONS (DATAIO-031)
- Publish tags a version only on a green CI: the gate of a release runs in Gitea Actions (DATAIO-032)
- Gate tag v1.25.8: CI on homeserver runs the gate as the Mac does (DATAIO-033)
- doctor is healthy on a server with env credentials: no false failure for the keychain, the provider or a missing project (DATAIO-034)

## v0.1.28 — 2026-10-21

### Outside epics

- Docs and comments name the Standard's sections, not cli-generator's internal files (DATAIO-030)

## v0.1.27 — 2026-10-21

### Outside epics

- CLI Standard v1.25.0: a usage error under --json prints the INVALID_ARGUMENTS envelope; the gate is gate check (DATAIO-029)

## v0.1.26 — 2026-10-18

### E-006 — Write: choose, order and rename the target columns

write(), convert() and dataio convert take columns (keep these, in this order) and rename (old -> new); every target (csv, xlsx, json, jsonl, parquet, stdout, Google Sheets, records in memory) gets the chosen columns under the new names; a wrong name or a clash is refused with exit 2. Released as a non-breaking 0.1.x; the tag goes to the semkit Architect.
Time: 0.3h since the epic was approved

- Target columns for templates, batch convert and Google Sheets (DATAIO-027)

## v0.1.25 — 2026-10-18

### E-006 — Write: choose, order and rename the target columns

write(), convert() and dataio convert take columns (keep these, in this order) and rename (old -> new); every target (csv, xlsx, json, jsonl, parquet, stdout, Google Sheets, records in memory) gets the chosen columns under the new names; a wrong name or a clash is refused with exit 2. Released as a non-breaking 0.1.x; the tag goes to the semkit Architect.
Time: 0.3h since the epic was approved

- dataio convert --columns/--rename, describe and docs (DATAIO-028)

## v0.1.24 — 2026-10-18

### E-006 — Write: choose, order and rename the target columns

write(), convert() and dataio convert take columns (keep these, in this order) and rename (old -> new); every target (csv, xlsx, json, jsonl, parquet, stdout, Google Sheets, records in memory) gets the chosen columns under the new names; a wrong name or a clash is refused with exit 2. Released as a non-breaking 0.1.x; the tag goes to the semkit Architect.
Time: 0.2h since the epic was approved

- Target columns in write(): select, order, rename for every single target (DATAIO-026)

## v0.1.23 — 2026-10-17

### Outside epics

- An int column with an empty cell reads as float from json, jsonl and Excel books (DATAIO-025)

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
