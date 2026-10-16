---
id: DATAIO-005
title: 'Backup safety fixes: content file name, no hard links, size check before parsing'
status: publish
attempts: 1
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
- src/rb_dataio/commands/
- tests/test_backup.py
- tests/test_protect.py
- tests/snapshots/
test_paths:
- tests/test_backup.py
- tests/test_protect.py
- tests/conftest.py
docs: none
tools: []
worker_args: null
class: standard
decision: false
visual: null
depends_on:
- DATAIO-002
budget_usd: null
epic: E-001
spec_refs: []
checks:
- python3 scripts/check_command_docstrings.py
- uv run scripts/release.py --check
resident: null
tool: null
pr: null
translation: 'Исправления резервных копий по ревью DATAIO-004: (1) файл содержимого
  копии назван по цели — цель entry.json затирает запись копии; (2) на одной ФС копия
  — жёсткая ссылка, правка цели другим инструментом меняет копию; (3) перед проверкой
  размера старая цель разбирается целиком (500 МБ+ читаются зря, и при backup=False
  тоже); (4) convert поверх источника при подтверждении читает источник дважды. Приёмка:
  по тесту на каждый пункт.'
---

Three defects found in the review of the protection task. A backup must stay a true, independent copy of the replaced data, and the size limit must save the cost it exists for.

- The kept content file is named after the target, so a target named like the entry file (entry.json) overwrites the backup entry.
- On the same file system the backup content is a hard link to the target; another tool that edits the target in place silently changes the kept copy.
- Before the size check the whole old target is parsed to count rows, so a 500 MB+ target is read in full only to be skipped; with backup=False it is parsed too.

## Acceptance

- Given a target named entry.json replaced twice, When backups lists it and restore runs, Then both backups are listed and restore brings back the exact previous content [check: tests/test_backup.py]
- Given a backup of a.csv, When another process rewrites a.csv in place (same inode), Then the kept backup content is unchanged and restore returns the old content [check: tests/test_backup.py]
- Given a target over the size limit, When it is replaced, Then the old target is not parsed (only its size is read), no copy is made and the report has the 'not copied' warning; Given backup=False, Then the old target is not parsed [check: tests/test_backup.py]
- Given convert over its own source refused and then confirmed, When dataio processes it, Then the source is read once [check: tests/test_protect.py]

## How to test

Integration tests through the public library API on temporary files; the size limit lowered through settings in the test; parse-count checked by patching the adapter read.

## Basis

Follow the existing backup and pipeline modules of the protection task; keep the backup entry format; use a fixed content file name inside the backup folder and a real copy (shutil.copy2).

## Read first

- `docs/adr/0005-rezervnaya-kopiya-vmesto-voprosov.md`
- `CODING_STANDARDS.md`

## Out of scope

- The append write path (no adapter appends yet); new parameters or flags.

## Feedback

### Attempt 1: file docstring

- update the docstring of src/rb_dataio/core/dataio/pipeline.py: +refuse_over_source
