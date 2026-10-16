---
id: DATAIO-004
title: 'Protection: backups, restore, atomic writes, write modes, safety checks and
  loss warnings'
status: in_progress
attempts: 0
blocked: true
blocked_reason: needs_scope
phase: null
tests_hash: null
publish_stage: null
created_by: architect
approved_by: human
worker: claude-code
type: feature
owns_paths:
- src/rb_dataio/core/dataio/protect.py
- src/rb_dataio/core/dataio/backup.py
- src/rb_dataio/core/dataio/pipeline.py
- src/rb_dataio/core/data_files.py
- src/rb_dataio/commands/backups.py
- src/rb_dataio/commands/restore.py
- src/rb_dataio/data/SKILL.md
- tests/test_backup.py
- tests/test_protect.py
- tests/snapshots/describe.json
- src/rb_dataio/data/settings.toml
- src/rb_dataio/commands/convert.py
- src/rb_dataio/core/dataio/api.py
- src/rb_dataio/core/dataio/options.py
- src/rb_dataio/core/dataio/protection.py
- src/rb_dataio/core/dataio/report.py
- src/rb_dataio/core/dataio/settings.py
- src/rb_dataio/core/errors.py
- tests/snapshots/help/convert.txt
- tests/snapshots/help/restore.txt
test_paths:
- tests/test_backup.py
- tests/test_protect.py
- tests/test_describe.py
- tests/conftest.py
- tests/snapshots/help/restore.txt
- tests/test_cli_frame.py
- tests/test_frame.py
docs:
- src/rb_dataio/data/SKILL.md
tools: []
worker_args: null
class: hard
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
translation: 'Защита: резервные копии, restore, атомарная запись, режимы записи, проверки
  безопасности и предупреждения о потерях.


  Любую перезапись можно откатить: перед заменой — копия, backups показывает, restore
  возвращает (сначала копируя текущее). Запись атомарная. mode=error отказывает при
  существующей цели. Запись поверх источника — только с разрешением. Предупреждения
  о потере строк и колонок, --dry-run показывает, что заменится. Лимиты копий.


  Приёмка: копия при замене; backups и restore с копией текущего; restore без --confirm
  — отказ, --dry-run, неизвестный id; --no-backup и лимиты (50 / 14 дней / 2 ГБ /
  > 500 МБ); падение посреди записи — файл цел; две записи сразу; mode=error; convert
  поверх источника; предупреждения о потерях; --dry-run с exists/rows_before/rows_after;
  хранилище в describe, опасные команды в SKILL.md.'
---

A user can undo any overwrite. Before dataio replaces an existing target it keeps a backup; `dataio backups` lists them and `dataio restore [ID]` brings the old content back (and first backs up the current content, so an undo can be undone). Writes are atomic, so a crash never leaves a broken file. mode=error refuses an existing target. Writing over the source itself needs explicit permission. The report warns when a replace drops most rows or loses columns, and --dry-run shows what would be replaced. Backups stay within limits.

This task fills the safety, backup and atomic-write hooks of the write pipeline and the backups/restore commands registered by the frame task.

## Acceptance

- Given out.csv exists, When write(df, 'out.csv') replaces it, Then a backup entry exists with id, time, target, rows and the old content [check: tests/test_backup.py]
- Given that backup, When 'dataio backups --json' runs, Then it lists the entry; When 'dataio restore --confirm' runs, Then out.csv has the old content and a new backup of the replaced content exists [check: tests/test_backup.py]
- Given 'dataio restore' under --non-interactive without --confirm, When dataio processes it, Then it is refused with the standard error and nothing changes; Given --dry-run, Then it shows what would be restored and nothing changes; Given an unknown id, Then SOURCE_NOT_FOUND lists the available ids [check: tests/test_backup.py]
- Given backup=False or --no-backup, When dataio processes it, Then no backup is made; Given 51 entries, or an entry older than 14 days, or more than 2 GB in total, Then the oldest are pruned; Given an object over 500 MB, Then it is not copied and the report has a warning [check: tests/test_backup.py]
- Given a write that raises midway, When dataio processes it, Then the old file is byte-for-byte intact and no temporary file is left [check: tests/test_protect.py]
- Given two processes writing the same target at once, When dataio processes it, Then the target ends as one complete version, never a mix, and each run has its own backup entry [check: tests/test_protect.py]
- Given mode='error' and an existing target, When dataio processes it, Then TARGET_EXISTS is raised and the file is unchanged; Given a missing target, Then it is written [check: tests/test_protect.py]
- Given convert('a.csv', 'a.csv'), When dataio processes it, Then TARGET_EXISTS is raised with action 'pass overwrite=True / --confirm'; Given overwrite=True, Then it runs with a backup [check: tests/test_protect.py]
- Given out.csv with 10000 rows replaced by 12 rows, When dataio processes it, Then the report warns 'replacing 10000 rows with 12'; Given lost columns, Then the warning names them [check: tests/test_protect.py]
- Given --dry-run on convert, When dataio processes it, Then the target part has exists, rows_before, rows_after and nothing is written or backed up [check: tests/test_protect.py]
- Given 'dataio describe --json', When dataio processes it, Then the backup store is listed in x-rb-data; Given the bundled SKILL.md, Then it names restore and convert-over-source as destructive and says to get the user's sign-off before --confirm [check: tests/test_describe.py]

## How to test

Integration tests through the public library API (write, convert, backups, restore) with the user data dir pointed at a temporary folder; CLI tests under --json through CliRunner for restore confirmation and --dry-run. Concurrency test with two processes writing the same target.

## Basis

Backup store in platformdirs.user_data_path (the template's way), declared in core/data_files.py DATA_FILES so describe --json shows it. Confirmation through output.require_confirmation and output.is_dry_run, as architecture §10 describes. Atomic write: temporary file in the target folder, then os.replace.

## Read first

- `docs/SPEC.md`
- `docs/adr/0001-biblioteka-i-cli-ravny.md`
- `docs/adr/0004-stroka-vsegda-adres.md`
- `CONTEXT.md`
- `CODING_STANDARDS.md`

## Out of scope

- Google Sheets confirmation and backups of remote sheets (google-http epic)
- Backups of sheets and base tables (their epics reuse this store)
- New CLI flags (the frame owns them)

## Feedback

### Answer to question #1

> DATAIO-004 acceptance wants convert-over-source refused with action 'pass overwrite=True / --confirm', but the convert command has --overwrite and no --confirm, and new CLI flags are out of scope.
> Question: How does the CLI allow a convert over its own source?
> Options:
> 1. Add output.ConfirmOption to convert: --confirm (or a yes at the prompt via require_confirmation) passes overwrite=True; keep --overwrite as the library parity flag
> 2. No new flag: the action names --overwrite for the CLI ('pass overwrite=True / --overwrite')
> Recommended: Add output.ConfirmOption to convert: --confirm (or a yes at the prompt via require_confirmation) passes overwrite=True; keep --overwrite as the library parity flag

Option 1, per SPEC (Confirmation section) and ADR 0005: add the template ConfirmOption to convert and use require_confirmation for convert-over-source; --confirm (or yes at the prompt) passes overwrite=True; keep --overwrite as the library parity flag. The action text: 'pass overwrite=True / --confirm'. Owns now include the convert and restore help snapshots.
