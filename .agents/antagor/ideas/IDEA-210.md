---
id: IDEA-210
title: 'dataio v1: one connector to read and write tables'
created: '2026-10-16T10:52:42+00:00'
source_project: dataio
source_path: /Users/bolandau/Work/tools/dataio
status: epic
for_path: /Users/bolandau/Work/tools/dataio
triage:
  serves: []
  risks: []
  why: Every tool rewrites table I/O; one connector removes this repeated work (goal
    of dataio)
  score: 8.0
  route: clarify
  at: '2026-10-16T10:52:49+00:00'
clarify_project: /Users/bolandau/Work/tools/dataio
clarify_since: '2026-10-16T10:52:49+00:00'
epic: E-001
---

One package (library + CLI with the same capabilities) reads any table source into a DataFrame and writes it to any target: Python objects, txt/csv/tsv/xlsx/json/jsonl/parquet, stdin/stdout, SQLite/DuckDB, Google Sheets, http(s); bulk merge/split; backups before overwrite. Tools (semkit first) stop writing their own I/O. Decisions: docs/brief.md.
