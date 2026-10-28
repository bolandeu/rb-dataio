---
id: IDEA-231
title: 'dataio: writing xlsx is quadratic'
created: '2026-10-17T17:29:47+00:00'
source_project: semkit
source_path: /Users/bolandau/Work/tools/semkit
status: dropped
for_path: /Users/bolandau/Work/tools/dataio
reason: 'Split into DATAIO-024 (xlsx write speed) and DATAIO-025 (int with gaps reads
  as float); triage refused: SPEC.md of dataio is a product spec, not P1..P11'
---

rb_dataio.write to xlsx grows quadratically: 2k rows 0.8 s, 10k 3.8 s, 30k 29 s, 100k 326 s, 1M did not end in 15 min; reading the same 100k-row xlsx takes 1.3 s, csv write of 1M rows 1.4 s. A killed write leaves its temp folder (.big.xlsx.XXXX/). Also: reading json/jsonl/xlsx turns an integer column with an empty cell into float (10 -> 10.0); csv and parquet keep Int64. Found by the semkit e2e check (semkit docs/plans/e2e-quality.md items 28, 51).
