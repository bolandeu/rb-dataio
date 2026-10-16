---
id: DATAIO-008
title: 'Containers in the core: files with named parts (sheets, tables), reading one
  or all, writing one part and keeping the rest'
status: queue
attempts: 1
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
- src/rb_dataio/core/
- src/rb_dataio/commands/
- src/rb_dataio/__init__.py
- src/rb_dataio/formats/__init__.py
- src/rb_dataio/formats/csv.py
- src/rb_dataio/formats/tsv.py
- src/rb_dataio/formats/txt.py
- src/rb_dataio/formats/json.py
- src/rb_dataio/formats/jsonl.py
- tests/conftest.py
- tests/test_containers.py
- tests/data/containers/
- tests/snapshots/
- tests/test_frame.py
- tests/test_cli_frame.py
test_paths:
- tests/test_containers.py
- tests/test_frame.py
- tests/test_cli_frame.py
- tests/test_backup.py
- tests/test_scripts.py
docs: none
tools: []
worker_args: null
class: hard
decision: false
visual: null
depends_on: []
budget_usd: null
epic: E-002
spec_refs: []
checks:
- python3 scripts/check_command_docstrings.py
- uv run scripts/release.py --check
resident: null
tool: null
pr: null
translation: 'Контейнеры в ядре: файлы с именованными частями (листы, таблицы). Адаптер
  формата может объявить себя контейнером: список частей, чтение одной части, запись
  одной части в существующий файл с сохранением остальных; запись начинается с копии
  файла, поэтому копия и атомарная запись работают; предупреждения адаптера попадают
  в отчёт. Ядро даёт всем контейнерам одно поведение: часть из адреса или sheet/table;
  первая по умолчанию; нет части — SOURCE_NOT_FOUND со списком; ''*'' — все части
  с колонкой _sheet и предупреждением при разных колонках; info показывает части;
  модули formats с ''_'' — не форматы. Проверка — тестовым форматом-контейнером. Нужна
  Excel (E-002), базам (E-003) и Google (E-004).'
---

Many formats hold several named tables in one file: Excel books have sheets, databases have tables, a Google spreadsheet has sheets. This task teaches the core about such containers once, so the Excel, database and Google formats only implement the format itself.

A format adapter may declare that it is a container: it lists the names of its parts, reads one named part, and writes one named part into an existing file while the other parts stay. A write to a container starts from a copy of the current file, so the atomic write and the backup of the whole file keep working. An adapter write may return warnings (for example, things that may be lost) and they reach the report. The core then gives every container the same behaviour: the part from the address fragment or the sheet/table parameter; the first part when none is named; a missing part is SOURCE_NOT_FOUND listing the parts; '*' reads all parts stacked with a _sheet column (a union of columns with a warning when they differ); info lists the parts. Helper modules of the formats package whose name starts with '_' are not formats.

The behaviour is proven with a small container format that lives only in the tests.

## Acceptance

- Given a test container file with parts A and B, When read('file#B') or read('file', sheet='B') runs, Then part B is returned; Given no part named, Then part A (the first) [check: tests/test_containers.py]
- Given a missing part 'C', When read, Then SOURCE_NOT_FOUND is raised and its message lists A and B [check: tests/test_containers.py]
- Given parts A (columns x, y) and B (columns x, z), When read('file#*') runs, Then the rows of both are returned with a _sheet column holding A or B, columns x, y, z, and one warning naming the differing columns; Given equal columns, Then no warning [check: tests/test_containers.py]
- Given a container with parts A and B, When write(df, 'file#B') runs, Then B holds df, A is byte-for-byte the same content, a backup of the whole file exists and restore brings the old B back [check: tests/test_containers.py]
- Given an adapter write that returns the warning 'charts may be lost', When write runs, Then the report warnings contain it [check: tests/test_containers.py]
- Given 'dataio info file --json' on a container, When it runs, Then the result has parts ['A', 'B']; Given a non-container CSV, Then there is no parts field or it is empty [check: tests/test_containers.py]
- Given a module named _helpers in the formats package, When formats() runs, Then it is not listed and nothing fails [check: tests/test_containers.py]

## How to test

Integration tests through the public library API and the CLI under --json; a container format defined in the tests (for example a zip of CSV files, one per part) registered the way the frame tests register their probe format.

## Basis

Extend the FormatAdapter contract and the read/write pipelines of the frame; keep the backup, atomic write and modes of the protection modules; follow how the frame tests add a probe format.

## Read first

- `docs/SPEC.md`
- `docs/adr/0004-stroka-vsegda-adres.md`
- `CONTEXT.md`
- `CODING_STANDARDS.md`

## Out of scope

- Any real container format (Excel, databases, Google); new parameters or flags.

## Feedback

### Answer to finding #1

> tests/test_scripts.py::test_antagor_project_config failed on main after commit 409d392 (antagor.toml [publish] gained regenerate = {uv.lock = 'uv lock'}). DATAIO-008 added the key to the expected dict so the gate passes; check that this is the wanted config.

Yes, regenerate = {uv.lock = 'uv lock'} is the wanted config (409d392).

### Attempt 1: file docstring

- update the docstring of src/rb_dataio/core/errors.py: +PartNotFound
