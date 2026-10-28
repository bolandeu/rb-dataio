---
id: IDEA-241
title: 'Write: choose, order and rename the columns of the output'
created: '2026-10-18T12:51:09+00:00'
source_project: semkit
source_path: /Users/bolandau/Work/tools/semkit
status: epic
for_path: /Users/bolandau/Work/tools/dataio
triage:
  serves: []
  risks: []
  why: Every CLI writing through dataio gets output column choice, order and names
    in one place, not per tool; open questions on append/merge targets and rename-vs-columns
    order
  score: 3.0
  route: clarify
  at: '2026-10-18T12:53:27+00:00'
clarify_project: /Users/bolandau/Work/tools/dataio
clarify_since: '2026-10-18T12:53:27+00:00'
epic: E-006
---

From semkit (the Human, 2026-10-18): the names of the output fields are the column names the steps make (phrase, match, similarity…); the user wants to choose which columns go out, in which order, and under which names, at write time, for every CLI that writes through dataio rather than by steps in each tool. Wish: dataio write takes columns (a list: keep these, in this order; an unknown name refused, naming the columns there are) and rename (a mapping old -> new; a clash refused), applied before any format (csv, xlsx, jsonl, stdout, Sheets); the dataio CLI exposes them (e.g. --columns phrase,similarity --rename similarity=сходство). semkit then passes them through its write step (write OUT --columns … --rename …). Send the release tag to the semkit Architect.
