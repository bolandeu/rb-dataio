---
id: IDEA-209
title: 'Universal table read/write: one read() and write() for every source'
created: '2026-10-16T10:29:20+00:00'
source_project: dataio
source_path: /Users/bolandau/Work/tools/dataio
status: dropped
for_path: /Users/bolandau/Work/tools/dataio
reason: 'Human: dataio is not run under Antagor'
---

dataio reads any table source into a pandas DataFrame and writes a DataFrame to any target, with one API and one CLI. Sources and targets: Python objects (str lines, list, list of dict, dict, Series, DataFrame), files (txt, csv, tsv with auto encoding and delimiter incl. cp1251, xlsx/xls/xlsb/ods via pandas calamine/openpyxl, json, jsonl, parquet), Google Sheets (gspread + service account), stdin/stdout, and simple databases DuckDB and SQLite (table or query). Why: every tool (semkit, serp, wordstat, bukvarix) rewrites this each time; no ready library covers all formats incl. Google Sheets (checked pandas, DuckDB gsheets, frictionless, pyexcel, pytablereader, readwrite, sq). Thin wrapper over pandas + gspread; own code only for source detection and defaults. CLI: dataio convert IN OUT.
