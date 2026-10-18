---
id: DATAIO-028
title: 'Docs: target columns in README, SKILL.md and SPEC'
status: ideas
attempts: 0
blocked: false
blocked_reason: null
phase: null
tests_hash: null
publish_stage: null
created_by: architect
approved_by: null
worker: claude-code
type: docs
owns_paths:
- README.md
- src/rb_dataio/data/SKILL.md
- docs/SPEC.md
test_paths: []
docs:
- README.md
tools: []
worker_args: null
class: mechanical
decision: false
visual: null
depends_on: []
budget_usd: null
epic: E-006
spec_refs: []
checks:
- python3 scripts/check_command_docstrings.py
- uv run scripts/release.py --check
resident: null
tool: null
pr: null
translation: 'Документация: колонки цели в README, SKILL.md и SPEC.


  README, скилл агента и спецификация описывают columns и rename: сначала выбор, потом
  переименование; отказы с exit 2; поведение со split_by и append; флаги --columns
  и --rename у dataio convert с примером из semkit. Термин — «Колонки цели».


  Готово, когда: README — пример API и CLI; SKILL.md — оба параметра, порядок, INVALID_ARGUMENTS
  со списком колонок; SPEC — новая история в «Writing» и выбор колонок при чтении
  в Out of Scope.'
---

The user docs, the agent skill and the spec describe the target columns: columns (keep these source columns, in this order) and rename (old -> new), the order selection then rename, the refusals with exit 2, how split_by and append behave with them, and the CLI flags --columns and --rename of dataio convert with the example from semkit. The glossary term is Колонки цели.

Done when:
1. README.md, the writing section, shows write(df, t, columns=[...], rename={...}) and dataio convert in.csv out.json --columns phrase,similarity --rename similarity=сходство.
2. SKILL.md names both options, the selection-then-rename order, and that a wrong name or a clash gives INVALID_ARGUMENTS (exit 2) with the list of columns.
3. docs/SPEC.md has a new Writing user story on choosing, ordering and renaming the target columns; Out of Scope names column choice on read.

## Out of scope

- Code and tests (DATAIO-026, DATAIO-027); CONTEXT.md (the term is already there).
