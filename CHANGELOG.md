# Changelog

All notable changes to this project are documented here. Versions follow
[SemVer](https://semver.org/) (while at `0.x`, a minor bump may break).

The changelog is written by `antagor publish`; don't edit it by hand.

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
