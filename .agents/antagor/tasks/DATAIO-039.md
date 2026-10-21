---
id: DATAIO-039
title: README states the package's own release facts only, not Antagor's process
status: in_review
attempts: 0
blocked: false
blocked_reason: null
phase: null
tests_hash: null
publish_stage: null
created_by: architect
approved_by: human
worker: claude-code
type: docs
owns_paths:
- README.md
- tests/test_scripts.py
test_paths:
- tests/test_scripts.py
docs:
- README.md
tools: []
worker_args: null
class: mechanical
decision: false
visual: null
depends_on: []
budget_usd: null
epic: null
spec_refs: []
checks:
- python3 scripts/check_command_docstrings.py
- uvx --from "git+https://homeserver.tailee01ab.ts.net:3000/bolandeu/cli-generator.git@v1.25.8#subdirectory=gate"
  rb-release check
resident: null
tool: null
pr: null
translation: README — только факты пакета о выпуске, без пересказа процесса Antagor
  (просьба cli-generator, шаблон v1.26.3). В разделе Release оставить строку «версия
  — git-тег», остальное (тикеты, кто выпускает, блок antagor publish, как собирается
  CHANGELOG, что делает deploy) заменить одной строкой «Work and releases go through
  Antagor». В Install «(a tag cut by antagor publish; never install a branch)» → «(never
  install a branch)». Тест раскладки больше не требует «antagor publish» в README.
---

A reader of the README learns the package's own release facts, not a retelling of Antagor's process (the request of cli-generator, template v1.26.3: Antagor's rules come from the installed Antagor, and a retelling goes stale). In the section Release: keep the line that the version is the git tag (vX.Y.Z, no version in the project metadata), and replace the rest (work through Antagor tickets, who runs a release, the antagor publish block, how the changelog is built, what the deploy script does) by one line: Work and releases go through Antagor. In Install: 'the latest release tag (a tag cut by antagor publish; never install a branch)' becomes 'the latest release tag (never install a branch)'. The layout test no longer asks the README for 'antagor publish' (the requirement changed); its other asserts stay. Nothing else changes.

## Acceptance

- Given the README, When the layout test reads it, Then it has no 'antagor publish' and no 'ticket', and the Release section still says the version is the git tag [check: tests/test_scripts.py]

## Out of scope

- the agents pointer file and the code rules: the Architect changed them on main
- the README sections Join, Target columns and the install commands
