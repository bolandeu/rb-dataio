# Plan: dataio v1

Source: `docs/brief.md` (interview, 2026-10-16), spec `docs/SPEC.md`, idea IDEA-210. Status: final (the Human, 2026-10-16).
Each epic ends in a working release; semkit can switch to dataio after the first one.

## Epics, in the order of work

### 1. core — the connector and its contract (→ 0.2)
- Address model: one string for source and target (`path#sheet`, `-`, schemes), parameters override the address (brief 3, 4).
- Public API `read`, `write`, `convert`, `info`, `formats` with one parameter vocabulary; `in_`/`out_` prefixes in `convert`; a parity test against CLI flags (35–39).
- Python objects in and out; txt, csv, tsv (encoding and delimiter detection, `excel` profile), json, jsonl; stdin/stdout (7–10, 12, 14, 21).
- Types and values: no NA words to empty, leading-zero rule, `as_text`, `dtypes`, empty rows skipped, header repair (7, 8).
- Write modes `replace|append|error`, atomic writes (20).
- `DataioError` = `CliError` with dataio codes; `--json` reports with `warnings`; `--dry-run`; `--limit` (26–29, 22, 23).
- Backups before overwrite, `backups`, `restore` with confirmation, shrink warnings (40–44, 47, 48).
- CLI: `convert`, `info`, `formats`, `backups`, `restore`; template `run` removed; help, SKILL.md (49, 50).

### 2. excel-parquet (→ 0.3)
- Excel read (xlsx/xls/xlsb/ods, calamine), `#sheet`, `#*` all sheets with `_sheet` (6, 11).
- xlsx write: replace one sheet, keep the others, autowidth, frozen header, autofilter, row limit (11).
- Parquet read/write through DuckDB (13).

### 3. databases-query (→ 0.4)
- SQLite and DuckDB: table by address or `table=`, `query=` into the base, write modes in one transaction, type mapping (15).
- `query=` over any source through DuckDB, table `data`; direct over csv/parquet files (3, 22).

### 4. google-http (→ 0.5)
- Provider `google` (service account, credential order, `health_check`, sharing hint on 403) (16, 45).
- Google Sheets read/write: URL and `gsheet://`, modes, create sheet, `start`, RAW values, batches, retries, cell limit, confirmation for replacing a non-empty sheet, backups of old values (17–19, 40).
- http(s) sources through `HttpProvider` (5, 46).

### 5. bulk (→ 0.6)
- Merge: globs, folders, lists, `_source`, `strict` → `SCHEMA_MISMATCH` (6, 30).
- Split: `{column}`, `{n}` with `split_by`, `chunk_rows`, to files and sheets (31).
- 1:1 conversion with `{stem}`; batch report, `keep_going`, `--dry-run` list (32, 33).

## Test seams (all epics)
1. The public library API.
2. The CLI under `--json` through `CliRunner`, plus the template's help/describe/auth snapshots.
3. Consumer contracts in `tests/contracts/`. Google and http tested with an injected client, no network.
