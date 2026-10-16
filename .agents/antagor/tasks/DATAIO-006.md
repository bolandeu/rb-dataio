---
id: DATAIO-006
title: Loss warnings come back for --no-backup; old backup entries stay restorable
status: done
attempts: 0
blocked: false
blocked_reason: null
phase: null
tests_hash: null
publish_stage: null
created_by: architect
approved_by: human
worker: claude-code
type: bugfix
owns_paths:
- src/rb_dataio/core/dataio/
- tests/test_backup.py
- tests/test_protect.py
test_paths:
- tests/test_backup.py
- tests/test_protect.py
docs: none
tools: []
worker_args: null
class: standard
decision: false
visual: null
depends_on:
- DATAIO-005
budget_usd: null
epic: E-001
spec_refs: []
checks:
- python3 scripts/check_command_docstrings.py
- uv run scripts/release.py --check
resident: null
tool: null
pr: null
translation: 'Предупреждения о потере строк и колонок вернуть для --no-backup: DATAIO-005
  перестала читать старую цель при backup=False, и предупреждения молча пропали (ошибка
  в моём пункте приёмки). Пропуск чтения — только для цели больше лимита копии. Копии
  старого формата (файл по имени цели) по-прежнему восстанавливаются.'
---

A replace that drops most rows or loses columns must warn whether a backup is kept or not: with --no-backup the warning is the only signal of a bad overwrite. The backup-safety fix stopped parsing the old target when backup is off, so these warnings silently vanished. Only a target over the backup object limit skips the parse (its size alone is read).

Backups made before the fixed content name keep their content under the target's file name; restore and backups must still find them.

## Acceptance

- Given out.csv with 10 rows and columns phrase,freq, When write(df with 1 row and column phrase, 'out.csv', backup=False) runs, Then the report has the warnings 'replacing 10 rows with 1' and 'columns lost: freq' [check: tests/test_protect.py]
- Given a target over the backup object limit, When it is replaced, Then the old target is still not parsed and the report has the 'no backup' warning [check: tests/test_backup.py]
- Given a backup entry whose content file is named after the target (the layout before the fixed name), When restore runs with its id, Then the old content comes back [check: tests/test_backup.py]

## How to test

Integration tests through the public library API on temporary files; the old layout is built by hand in the backup store of the data_dir fixture.

## Basis

pipeline._state and backup.content of the protection modules; replace the test that asserts backup=False does not parse with the warning test above.

## Out of scope

- New parameters or flags; the append path.
