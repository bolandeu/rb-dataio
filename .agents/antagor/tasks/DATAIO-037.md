---
id: DATAIO-037
title: 'Docs of join: the skill and the README show a VLOOKUP-like join by two keys'
status: publish
attempts: 0
blocked: true
blocked_reason: idea_wait
phase: null
tests_hash: null
publish_stage: null
created_by: architect
approved_by: human
worker: claude-code
type: docs
owns_paths:
- src/rb_dataio/data/SKILL.md
- README.md
- tests/test_describe.py
test_paths:
- tests/test_describe.py
docs:
- src/rb_dataio/data/SKILL.md
- README.md
tools: []
worker_args: null
class: mechanical
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
translation: 'Документация join: навык и README показывают соединение как ВПР по двум
  ключам — пример dataio join main.csv out.xlsx --lookup prices.xlsx#Prices --on phrase
  --on region и join() в Python; правила: ключи всегда явно (--on, main=lookup), --how
  left/inner/right (только один справочник)/full, сравнение как текст без пробелов
  по краям, пустой ключ ни с чем не совпадает, повтор ключа добавляет строки и предупреждает,
  суффикс _<имя справочника>, отчёт с нашли/не нашли, join поверх своего источника
  — разрушительный, подтверждение перед --confirm.'
---

An agent that reads the bundled skill, and a person who reads the README, learn dataio join: what it does (the lookups' columns put next to the main rows by named key columns, as VLOOKUP), the call dataio join main.csv out.xlsx --lookup prices.xlsx#Prices --on phrase --on region, and its library form join(source, target, lookups=[...], on=[...]). The rules to state: keys are always named (--on, main=lookup for different names), never taken from same-named columns; --how left (default), inner, right (one lookup only), full; keys compare as text with outer spaces trimmed, case and ё kept; an empty key matches nothing; a key repeated in a lookup adds rows and warns; a same-named lookup column gets the suffix _<lookup name>; the report counts matched and unmatched rows per lookup; a join whose target is one of its sources is destructive like convert's and is signed off before --confirm. The terms are those of CONTEXT.md (Соединение, Справочник), in the language of each file.

## Acceptance

- Given the bundled SKILL.md, When the skill test reads it, Then it has a join section with the example dataio join ... --lookup ... --on phrase --on region and the words --on, --lookup, --how, VLOOKUP [check: tests/test_describe.py]
- Given README.md, When the docs test reads it, Then it has dataio join with --on phrase --on region and join( in Python [check: tests/test_describe.py]

## Read first

- `src/rb_dataio/data/SKILL.md`
- `CONTEXT.md`

## Out of scope

- the command and the function themselves: DATAIO-035 and DATAIO-036
- docs/SPEC.md and CONTEXT.md: the Architect's
