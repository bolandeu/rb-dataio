---
id: DATAIO-036
title: 'dataio join: the CLI command over join(), with the flags of convert'
status: publish
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
- src/rb_dataio/commands/join.py
- src/rb_dataio/cli.py
- tests/test_cli_join.py
- tests/test_parity.py
- tests/snapshots/help/
- tests/contracts/
- tests/data/cli_join/
- tests/test_help.py
- src/rb_dataio/commands/_parameters.py
test_paths:
- tests/test_cli_join.py
- tests/test_parity.py
- tests/test_help.py
- tests/snapshots/describe.json
docs: none
tools: []
worker_args: null
class: standard
decision: false
visual: null
depends_on:
- DATAIO-035
budget_usd: null
epic: E-007
spec_refs: []
checks:
- python3 scripts/check_command_docstrings.py
- uvx --from "git+https://homeserver.tailee01ab.ts.net:3000/bolandeu/cli-generator.git@v1.25.8#subdirectory=gate"
  rb-release check
resident: null
tool: null
pr: null
translation: 'dataio join — команда CLI поверх join(): dataio join SOURCE TARGET --lookup
  АДРЕС --on КЛЮЧ [--how left|right|inner|full], флаги чтения --in-* и записи --out-*
  как в convert, --lookup и --on повторяются. Тот же отчёт, что у join(): в человеческом
  виде по каждому справочнику нашли/не нашли/пустые ключи, под --json — конверт с
  lookups. Подтверждение замены (цель — один из источников, Google-лист со строками)
  и --confirm как в convert; цель - — данные в stdout. Отказы с INVALID_ARGUMENTS
  (код 2): нет --on, неизвестный --how, right с двумя справочниками, нет колонки-ключа.
  Тест паритета: каждый параметр join() — флаг с тем же именем. Снимок справки с примером
  left по двум ключам, describe показывает join.'
---

A CLI user runs dataio join SOURCE TARGET --lookup ADDRESS --on KEY [--how left|right|inner|full] and gets the same join and the same report as the library join() (ADR 0001: every keyword of join() is a flag of the same name; --lookup and --on repeat; the read options take --in-, the write options --out-, as in convert). The command maps the flags to one join() call, as convert maps to convert(): the human report shows each lookup's matched / unmatched / empty keys; under --json the envelope carries the report with lookups. A replace that needs confirmation (a target that is one of the sources, a Google sheet with rows) asks first, --confirm skips the question, as in convert. Target - is stdout: the data, as in convert.

## Acceptance

- Given main.csv (sku,name: 1,a / 2,b) and prices.csv (sku,price: 1,10), When dataio join main.csv out.csv --lookup prices.csv --on sku --json runs, Then it exits 0 with ok true, the report has lookups [{uri: prices.csv, rows: 1, matched: 1, unmatched: 1, empty_keys: 0}], and out.csv read back has sku,name,price with 1,a,10 and 2,b,empty [check: tests/test_cli_join.py]
- Given --on phrase --on region, --on sku=article, two --lookup and --how inner/right/full, When dataio join runs, Then they reach join() as on=[...], lookups=[...], how=... and give its result [check: tests/test_cli_join.py]
- Given no --on, --how other, --how right with two --lookup, or a key column a source lacks, When dataio join --json runs, Then it exits 2 with the INVALID_ARGUMENTS envelope (the missing column's message names the source, the column and its columns) and no target is written [check: tests/test_cli_join.py]
- Given --dry-run, When dataio join runs, Then the report has the lookups counts and the target is not written; Given the target is main.csv itself, When dataio join runs without --confirm under --json, Then it is refused as convert refuses it, and with --confirm it writes and keeps a backup that dataio restore brings back [check: tests/test_cli_join.py]
- Given the target -, When dataio join runs, Then stdout is the joined data as convert writes it to -, and under --json the data is records inside the envelope [check: tests/test_cli_join.py]
- Given join() and dataio join, When the parity test runs, Then every keyword of join() is a flag with the same name and default (a list is a repeatable flag), and a missing or an extra flag fails [check: tests/test_parity.py]
- Given dataio join --help and dataio describe --json, When they run, Then the help snapshot shows the command with an example of a left join by two keys, and describe lists join with --lookup, --on and --how [check: tests/test_help.py]

## How to test

Seam 2, the CLI under --json through CliRunner (the invoke_json helper the CLI tests of convert use); small csv files under tmp_path, the target read back with read(); the help snapshot updated with --snapshot-update and reviewed. No network.

## Basis

Follow the convert command: its flags (the option() helper with in_/out_), the confirmation of a replace, the target - and render_report; join only adds --lookup, --on, --how and the lookups lines of the human report. The parity test takes join() the way it takes convert() and info().

## Read first

- `src/rb_dataio/commands/convert.py`
- `src/rb_dataio/commands/_parameters.py`
- `tests/test_parity.py`

## Out of scope

- the join behaviour itself (kinds, keys, empty and repeated keys, suffixes): DATAIO-035; a defect found there goes back to it as a note
- SKILL.md and README.md: the docs task of this epic
- new flags beyond join()'s keywords

## Feedback

### Answer to finding #1

> rb-release check runs pytest with forced colour: 28 old tests fail on ANSI codes (test_auth, test_backup, test_bases_core, test_cli, test_cli_frame, test_cli_target_columns, 20 help snapshots incl. join). The same tests pass in a plain 'uv run pytest'. Outside DATAIO-036; the join tests pass in both modes.

Fixed outside the task: DATAIO-031 (tests plain under GITHUB_ACTIONS/FORCE_COLOR) and DATAIO-032/033 (the [publish] table, gate v1.25.8) are in main since v0.1.29, whose CI ran gate v1.25.8 green; the branch was cut before them.
