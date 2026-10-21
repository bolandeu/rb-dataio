---
id: DATAIO-035
title: 'join() in the library: a main source and lookups joined by named key columns'
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
- src/rb_dataio/core/dataio/
- src/rb_dataio/__init__.py
- src/rb_dataio/core/errors.py
- tests/test_join.py
- tests/data/join/
- src/rb_dataio/data/settings.toml
test_paths:
- tests/test_join.py
docs: none
tools: []
worker_args: null
class: hard
decision: false
visual: null
depends_on: []
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
translation: 'join() в библиотеке: основной источник и справочники соединяются по
  названным ключевым колонкам. Вся логика соединения: left по умолчанию (порядок строк
  основного источника, пустые колонки без пары), несколько ключей вместе, sku=article,
  отказ INVALID_ARGUMENTS без on или без колонки-ключа (с именем источника и его колонками),
  inner/right/full (ключ — со стороны, где он есть), несколько справочников по очереди,
  right — только с одним, ключи как текст без пробелов по краям (регистр и ё различаются,
  тип ключа основного источника сохраняется), пустой ключ ни с чем не совпадает и
  считается, повтор ключа — все совпадения и предупреждение, одинаковые колонки —
  суффикс _<имя справочника>, запись — путём convert (режимы, копия, restore, отказ
  писать поверх источника, dry_run), источники — объекты Python и адреса. Отчёт: новый
  список lookups (address, rows, matched, unmatched, empty_keys). Команда CLI и документация
  — в своих задачах.'
---

A library user calls join(source, target, lookups=[...], on=[...], how='left') and gets the main table with the lookups' columns, matched by the named key columns, written to any target that convert takes, and a report that says how many main rows found a match in each lookup. This task holds the whole join behaviour (kinds, keys, many lookups, empty and repeated keys, same-named columns); the CLI command dataio join comes in its own task on top of this function.

Shape of the call (keywords as convert's, ADR 0001): join(source, target, *, lookups, on, how='left', the read options of convert with in_ that apply to every source, the write options of convert with out_, mode, start, value_input, columns, rename, overwrite, backup, dry_run) -> Report. on is a list of items, each a column name or main_name=lookup_name. how is one of left, right, inner, full. The report gets a new list lookups: one entry per lookup with address, rows, matched, unmatched, empty_keys.

The terms are in CONTEXT.md: Соединение (join), Справочник (lookup).

## Acceptance

- Given main [{sku: 1, name: a}, {sku: 2, name: b}, {sku: 3, name: c}] and a lookup [{sku: 2, price: 20}, {sku: 1, price: 10}], When join(main, target, lookups=[lookup], on=['sku']) runs with no how, Then the target has the rows sku 1, 2, 3 in this order with price 10, 20 and empty, and report.lookups[0] has rows 2, matched 2, unmatched 1, empty_keys 0 [check: tests/test_join.py]
- Given on=['phrase', 'region'], When join runs, Then a main row matches a lookup row only when both phrase and region are equal ('купить', 213 does not match 'купить', 2) [check: tests/test_join.py]
- Given on=['sku=article'], When join runs, Then sku of the main source matches article of the lookup and the result has one key column, sku, and no article column [check: tests/test_join.py]
- Given on=[] or no on, or a key column that the main source or a lookup does not have, When join runs, Then it raises INVALID_ARGUMENTS (exit 2); the message of a missing column names the source, the column and that source's columns; nothing is written [check: tests/test_join.py]
- Given main keys 1, 2 and lookup keys 2, 3, When how is inner, right or full, Then the keys of the result are 2; 2, 3; 1, 2, 3, and the key column takes its value from the side that has it [check: tests/test_join.py]
- Given two lookups, When how is left, inner or full, Then each is joined to the main source in the given order with the same keys; When how is right with two lookups, Then it raises INVALID_ARGUMENTS and nothing is written [check: tests/test_join.py]
- Given the main key 123 (an int) and lookup keys '123' and ' 123 ' (text), When join runs, Then both match (keys compared as text with outer spaces trimmed) and the key column stays int; Given 'A' and 'a', or 'Ёлка' and 'Елка', Then they do not match [check: tests/test_join.py]
- Given a main row whose key cell is empty, When join runs with left, Then the row stays with empty lookup columns, matches nothing (also not an empty key of the lookup), and report.lookups[0].empty_keys counts it [check: tests/test_join.py]
- Given the key 2 twice in a lookup, When join runs, Then the main row with key 2 comes out twice (once per match) and the report has a warning that names the repeated key 2 (at most the first 5 keys) and the number of rows added, 1 [check: tests/test_join.py]
- Given a column name in both the main source and the lookup prices.xlsx#Prices that is not a key, When join runs, Then the main column keeps its name and the lookup's is name_Prices (the part of its address, else the file stem; a Python object lookup is lookup1, lookup2 by position; a suffix taken twice gets _2), and columns/rename then choose and name the target columns as in convert [check: tests/test_join.py]
- Given a target, When join writes, Then it goes through convert's write path: mode replace/append/error, a backup that restore() brings back, WriteOverSource for a target that is one of the sources without overwrite=True, dry_run=True gives the report with the lookups counts and writes nothing [check: tests/test_join.py]
- Given the sources as Python objects (a DataFrame, a list of dicts) or addresses (csv, an xlsx part), When join runs, Then both work, read through the same read path as read() [check: tests/test_join.py]

## How to test

Seam 1, the library join() as a library user calls it (from rb_dataio import join): small tables as Python objects and as files under tmp_path (csv, xlsx through write()); the target read back with read(); the report checked through to_dict(). No network.

## Basis

Read sources with pipeline.read_frame and write with pipeline.write_frame, as convert() does (refuse_over_source too); the join itself in DuckDB over the frames, as query.py runs SQL over a frame (ADR 0002 thin wrapper, ADR 0003 DuckDB). Errors: InvalidParameter for a wrong input. Report fields: follow SourcePart/TargetPart in report.py.

## Read first

- `src/rb_dataio/core/dataio/api.py`
- `src/rb_dataio/core/dataio/pipeline.py`
- `src/rb_dataio/core/dataio/query.py`
- `CONTEXT.md`

## Out of scope

- the CLI command dataio join, its flags, help and the parity test: the next task of this epic
- SKILL.md and README.md: the docs task of this epic
- anti join, a first-match mode, key normalisation (case, ё), fuzzy matching, keys per lookup, query= in join, a result in memory with no target
