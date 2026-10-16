---
id: DATAIO-015
title: 'Google Sheets: read and write sheets by URL or gsheet://, RAW values, batches,
  backoff, backups'
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
- src/rb_dataio/formats/gsheet.py
- tests/test_gsheet.py
- tests/data/gsheet/
test_paths:
- tests/test_gsheet.py
docs: none
tools: []
worker_args: null
class: hard
decision: false
visual: null
depends_on:
- DATAIO-014
budget_usd: null
epic: E-004
spec_refs: []
checks:
- python3 scripts/check_command_docstrings.py
- uv run scripts/release.py --check
resident: null
tool: null
pr: null
translation: 'Google Sheets через gspread: лист по gid или gsheet://id#Лист; не расшарено
  — AUTH_REQUIRED «Share the sheet with <email> as Editor»; нет листа — создаётся;
  start=''A5''; запись RAW (007 и =1+1 как текст), value_input=''user'' — USER_ENTERED;
  замена непустого листа с подтверждением (ядро), копией значений и restore, формат
  листа сохраняется; пачки по 10 000 строк, повтор при 429/5xx, > 10 млн ячеек — ошибка
  до записи. Тесты на фейковом клиенте, без сети.'
---

A user reads and writes a Google Sheet like a file, through gspread and the google key of the core. The sheet comes from the URL gid or the gsheet:// fragment. A sheet not shared with the service account is AUTH_REQUIRED saying 'Share the sheet with <email> as Editor'. A missing sheet name on write creates the sheet; start places the data. Values go RAW by default ('007' stays 007, '=1+1' stays text); value_input='user' lets Google parse them. Replace of a non-empty sheet needs confirmation (core), keeps the old values as a backup that restore puts back, and keeps the sheet formatting (values only are cleared and written). Writes go in batches of 10 000 rows with backoff on 429 and 5xx; more than 10 million cells is refused before anything is written. Modes replace, append and error work as for other containers.

## Acceptance

- Given a fake spreadsheet with sheets Sheet1 (gid 0) and Data (gid 123), When read with the browser URL '#gid=123', Then Data is returned; Given 'gsheet://ID#Sheet1', Then Sheet1 [check: tests/test_gsheet.py]
- Given the fake client raising the 403 of an unshared sheet, When read or written, Then AUTH_REQUIRED says 'Share the sheet with <the service-account email> as Editor' [check: tests/test_gsheet.py]
- Given a missing sheet 'New', When written, Then it is created; Given start='A5', Then the header lands in A5 [check: tests/test_gsheet.py]
- Given values '007' and '=1+1', When written, Then the update call uses RAW and the cells are the strings 007 and =1+1; Given value_input='user', Then USER_ENTERED is used [check: tests/test_gsheet.py]
- Given a confirmed replace of a non-empty sheet, When it ends, Then backups() has the old values, restore puts them back, and only values were cleared (no formatting call) [check: tests/test_gsheet.py]
- Given 25 000 rows, When written, Then three update calls of 10 000, 10 000 and 5 000 rows; Given a 429 then success, Then the batch is retried after a backoff; Given more than 10 000 000 cells, Then WRITE_FAILED before any call [check: tests/test_gsheet.py]
- Given 'dataio formats --json', When it runs, Then gsheet is listed with read, write and append [check: tests/test_gsheet.py]

## How to test

Integration tests through the public library API and the CLI under --json with an injected fake gspread client recording the calls; no network.

## Basis

The remote container contract and the google key of DATAIO-014; gspread; the backup of parts as parquet from DATAIO-011; the retry pattern of the template HttpProvider.

## Read first

- `docs/SPEC.md`
- `CODING_STANDARDS.md`

## Out of scope

- Creating spreadsheets; formatting of written sheets; OAuth user login; http(s) sources.
