---
id: DATAIO-002
title: 'CSV, TSV and txt: encoding and delimiter detection, the excel profile, and
  value normalisation'
status: queue
attempts: 0
blocked: false
blocked_reason: null
phase: null
tests_hash: null
publish_stage: null
created_by: architect
approved_by: human
worker: claude-code
type: feature
owns_paths:
- src/rb_dataio/formats/csv.py
- src/rb_dataio/formats/tsv.py
- src/rb_dataio/formats/txt.py
- src/rb_dataio/core/dataio/values.py
- tests/test_csv.py
- tests/test_values.py
- tests/data/csv/
test_paths:
- tests/test_csv.py
- tests/test_values.py
docs: none
tools: []
worker_args: null
class: standard
decision: false
visual: null
depends_on:
- DATAIO-001
budget_usd: null
epic: E-001
spec_refs: []
checks:
- python3 scripts/check_command_docstrings.py
- uv run scripts/release.py --check
resident: null
tool: null
pr: null
translation: 'CSV, TSV и txt: определение кодировки и разделителя, профиль excel,
  нормализация значений.


  Пользователь читает CSV из Excel и 1C без параметров (cp1251, UTF-8-BOM; '';'',
  таб, ''|''), отчёт показывает догадки. txt и списки фраз → колонка text. NA-слова
  остаются строками, ведущие нули и длинные ID — текст, пустые строки выкидываются.
  Запись CSV для Excel — профиль excel.


  Приёмка: cp1251/'';'' сами и в отчёте; BOM; ручные encoding/sep; tsv; ''|''; запись
  UTF-8 '','' и профиль excel; append с той же/другой шапкой; txt; NA-слова и пусто;
  ведущие нули, числа, даты; as_text, dtypes, ошибка преобразования; починка шапки
  и header=False; пустые строки; битый файл → READ_FAILED.'
---

A user reads CSV files from Excel and 1C without options: cp1251 or UTF-8 with BOM, ';' or tab or '|', and gets correct Cyrillic. The report names what was detected. txt files and phrase lists become one column 'text'. Values keep their meaning: 'NA' and friends stay strings, leading zeros and long IDs stay text, empty rows are dropped. Writing CSV for Excel is one option.

This task fills the value-normalisation step of the read pipeline (it applies to every format) and extends the CSV adapter; it adds txt and tsv adapters.

## Acceptance

- Given a cp1251 CSV with ';' and Cyrillic, When read, Then the text is correct; When convert or info runs, Then the report has encoding 'cp1251' and delimiter ';' [check: tests/test_csv.py]
- Given a UTF-8-BOM CSV, When dataio processes it, Then the first column name has no BOM; Given encoding='cp1251' or sep='|' passed, Then they are used instead of detection [check: tests/test_csv.py]
- Given a .tsv file, When dataio processes it, Then it is read with tab without sniffing; Given a '|' CSV, Then '|' is detected [check: tests/test_csv.py]
- Given write(df, 'out.csv'), When dataio processes it, Then the file is UTF-8 without BOM with ',' and '\n'; Given profile='excel', Then UTF-8-BOM with ';' [check: tests/test_csv.py]
- Given mode='append' to a CSV with the same header, When dataio processes it, Then rows are added below; Given another header, Then WRITE_FAILED is raised naming both headers and the file is unchanged [check: tests/test_csv.py]
- Given a txt file with lines 'a', '', 'b', When read, Then one column 'text' with rows 'a','b'; When a one-column frame is written to .txt, Then one value per line [check: tests/test_csv.py]
- Given cells 'NA', 'null', 'nan', 'None', '-', When dataio processes it, Then they stay strings; Given an empty cell, Then it is missing and is written back as an empty cell [check: tests/test_values.py]
- Given a column with '007' or '+79001234567' or '1234567890123456', When dataio processes it, Then it stays text; Given '1','2','3', Then it is an integer column; Given ISO dates, Then a date column [check: tests/test_values.py]
- Given as_text=True, When dataio processes it, Then every column is str; Given dtypes={'freq': 'int'}, Then freq is int; Given a value that cannot convert, Then READ_FAILED names the column and the value [check: tests/test_values.py]
- Given header names '', 'phrase', 'phrase', When read, Then columns are col1, phrase, phrase_2 and the report has one warning naming the repairs; Given header=False, Then columns are col1..colN [check: tests/test_values.py]
- Given rows where every cell is empty, When dataio processes it, Then they are dropped [check: tests/test_values.py]
- Given a binary or undecodable file with .csv, When dataio processes it, Then READ_FAILED names the address and the cause [check: tests/test_csv.py]

## How to test

Integration tests through the public library API (read, write, convert, info) on fixture files: cp1251 with ';', UTF-8-BOM with ',', tab, '|', headerless, empty and duplicate header names, NA words, leading zeros, 16-digit IDs, blank lines.

## Basis

Extend the CSV adapter of the frame task; add txt and tsv as new modules of the formats package (the registry finds them). pandas read_csv with keep_default_na=False and na_values=[''] for the NA rule; csv.Sniffer limited to , ; tab | on the first 64 KB. Report fields encoding and delimiter come from the adapter.

## Read first

- `docs/SPEC.md`
- `docs/adr/0001-biblioteka-i-cli-ravny.md`
- `docs/adr/0004-stroka-vsegda-adres.md`
- `CONTEXT.md`
- `CODING_STANDARDS.md`

## Out of scope

- Python objects, JSON, stdin/stdout
- Backups and atomic writes
- Excel cell types (Excel epic)
- Any change to the public API or CLI flags (the frame owns them)
