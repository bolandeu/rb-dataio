---
id: DATAIO-007
title: Release installs the new tag on this Mac
status: in_review
attempts: 0
blocked: false
blocked_reason: null
phase: null
tests_hash: null
publish_stage: null
created_by: architect
approved_by: architect
worker: claude-code
type: chore
owns_paths:
- scripts/deploy.sh
test_paths:
- tests/test_scripts.py
docs: none
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
- uv run scripts/release.py --check
resident: null
tool: null
pr: null
---

After every release the dataio CLI on this Mac must be the released version without any manual command. The deploy step of the release, right after pushing main with tags and before the release notice, installs the new tag as a uv tool from the origin remote (from the tag, never editable, as the tools root AGENTS.md requires) and prints dataio --version. A failed local install prints a warning to stderr and does not fail the release. Update the comment at the top of the script to say it also installs the tag on this Mac.

The line to add: uv tool install --force --quiet "rb-dataio @ git+$(git remote get-url origin)@$ANTAGOR_VERSION" && dataio --version || echo "warning: local install of $ANTAGOR_VERSION failed" >&2

## Out of scope

- Server deploys; the release notice.
