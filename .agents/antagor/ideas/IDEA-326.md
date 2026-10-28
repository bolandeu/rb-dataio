---
id: IDEA-326
title: 'join: VLOOKUP-like join of a main source with lookup sources by explicit key
  columns'
created: '2026-10-21T07:01:09+00:00'
source_project: dataio
source_path: /Users/bolandau/Work/tools/dataio
status: epic
for_path: /Users/bolandau/Work/tools/dataio
triage:
  serves: []
  risks: []
  why: a new command; the grill is under way
  score: null
  route: clarify
  at: '2026-10-21T07:01:12+00:00'
clarify_project: /Users/bolandau/Work/tools/dataio
clarify_since: '2026-10-21T07:01:12+00:00'
epic: E-007
before_epic: clarifying
---

The Human, 2026-10-21: a command like VLOOKUP to join several lists. Decided in the grill (round 1, all recommendations accepted): a new command `dataio join` and `join()` in the library, on DuckDB (already in dataio); a main source and one or more lookup sources, each joined to the main one; kinds left (default, = VLOOKUP), right, inner, full; no anti for now; several key columns match together (AND); keys are always named explicitly (`--on phrase --on region`, `--on phrase=query` for different names), never inferred from same-named columns; keys compared as text with outer spaces trimmed, case and yo kept; a key repeated in a lookup gives all matches (as SQL) plus a report warning; a key stays one column, a same-named non-key column of a lookup gets a suffix with the lookup's name; columns/rename choose the target columns; the target is any target, with write modes and backups, as in convert. Term: Соединение (join), not «объединение» (that is stacking rows).
