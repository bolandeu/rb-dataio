---
id: DATAIO-038
title: 'join: the repeated-keys warning names only keys that are repeated in the lookup'
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
type: bugfix
owns_paths:
- src/rb_dataio/core/dataio/joins.py
- tests/test_join.py
test_paths:
- tests/test_join.py
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
translation: 'join: предупреждение о повторяющихся ключах называет только ключи, которые
  действительно повторяются в справочнике. Сейчас строка основного списка без пары
  даёт номер строки справочника -1, и предупреждение берёт последнюю строку справочника:
  при основном 1, 2, 3 и справочнике 1, 1, 3 оно называет 1 и 3, хотя повторяется
  только 1. Исправить выбор строк (только пары, где есть обе стороны); текст, лимит
  и число добавленных строк — как есть.'
---

The warning of a join about repeated lookup keys can name a key that is not repeated. A main row with no match pairs with lookup row -1 (none); the warning takes the lookup rows of every pair whose main side is set, so -1 selects the last lookup row by position, and that row's key looks repeated. Example: main keys 1, 2, 3 and lookup keys 1, 1, 3 with left: the warning names 1 and 3, while only 1 is repeated. The warning must name exactly the lookup keys that matched a main row more than once, and the count of rows added stays as it is.

## Acceptance

- Given main keys 1, 2, 3 and lookup keys 1, 1, 3, When join runs with left, Then the warning names the key 1 only (not 3) and says 1 row added [check: tests/test_join.py]
- Given main keys 1, 2 and lookup keys 2, 2, 5, When join runs with full, Then the warning names the key 2 only and says 1 row added, and the lookup-only row 5 is not named [check: tests/test_join.py]
- Given no repeated lookup key, When join runs with any how, Then there is no warning about repeated keys [check: tests/test_join.py]

## How to test

Seam 1, the library join() on Python objects (lists of dicts), as the existing tests of the join do; the warning read from the report. No network.

## Basis

Fix the selection of the matched lookup rows in the warning of repeated keys (the function that builds it in the join module): only pairs with both sides set. Keep its text, the limit of named keys from the settings and the rows-added count.

## Out of scope

- the join itself, the report counts and the CLI
