# Brief: dataio

Read this file first. It is the hand-off from the session that created this repo.

## Goal
`dataio` reads any table source into a `pandas.DataFrame` and writes a DataFrame to any target, with one Python API (`read()`, `write()`) and a CLI with the same capabilities (`dataio convert IN OUT`). Other tools (first `semkit`, later serp, wordstat, bukvarix) use it, so they stop rewriting this I/O.

## Decided
1. Library and CLI have parity: the CLI exposes every `read()`/`write()` option as a flag. Logic lives in the library; the CLI only maps flags to it.
2. Sources and targets: Python objects (str lines, list, list of dict, dict, Series, DataFrame); files: txt, csv, tsv (auto encoding incl. cp1251, auto delimiter), xlsx/xls/xlsb/ods, json, jsonl, parquet; Google Sheets; stdin and stdout; DuckDB and SQLite.
3. Engines: pandas; Excel read `python-calamine`, Excel write `openpyxl`; Google Sheets `gspread` + a service account (the file is at `~/Work/credentials/google_service_account.json`); DuckDB; stdlib `sqlite3`.
4. No ready library covers all of this (checked: pandas, DuckDB gsheets, frictionless, pyexcel, pytablereader, readwrite, sq). Write a thin wrapper; own code only for source detection and defaults.
5. Private repo, private tool.
6. **Use the Antagor method in `fast` mode** (the Human changed this in the interview, 2026-10-16). The interview below is the clarification; then the spec (epic cards) and the slicing go through Antagor. Gate before each commit: `uv run scripts/release.py --check`. TDD: the failing test is committed first.
7. Repo state: cli-generator v1.15.0 scaffold, tag `v0.1.0`, no business logic yet. Names: dist `rb-dataio`, command `dataio`, import `rb_dataio`.

## Your first step
Run the interview below with the Human, in Russian, one block at a time. Each question has a recommendation (**R**); the Human can answer «R». Record the answers in this file (replace **R** with the decision), then write the plan, then code.

## Context (read only what you need)
- Why the tool exists and the full discussion summary: `/Users/bolandau/Work/_sandbox/semtools/docs/interviews.md` (top part).
- Sibling tool: `~/Work/tools/rb-semkit` (phrase processing, will depend on dataio).

## Сессия 1. dataio

### A. Назначение и потребители
1. **Кто первым использует dataio?** semkit, serp, wordstat, bukvarix, твои скрипты. **Решение:** semkit.
2. **Что важнее: библиотека или CLI?** **Решение:** равные возможности. Всё, что умеет `read()`/`write()`, доступно флагами CLI; логика — в библиотеке. Цель — один пакет-коннектор вместо своих функций I/O в каждом инструменте.

### B. Источники и адресация
3. **Как адресовать лист, таблицу или запрос одной строкой?** Варианты: `book.xlsx#Лист1`, `data.duckdb#phrases`, `gsheet://<id>#Лист1`; запрос — отдельным параметром `query=`. **Решение:** один адрес-строка для чтения и записи: `book.xlsx#Лист1`, `data.duckdb#phrases`, `-` (stdin/stdout), `gsheet://<id>#Лист1` и обычная ссылка `https://docs.google.com/spreadsheets/d/...` (лист по `gid`). Всё из адреса можно задать параметром (`sheet=`, `table=`, `format=` / `--sheet`, `--table`, `--format`), параметр важнее. `query=` / `--query` — поверх любого источника через DuckDB, таблица зовётся `data`; для `.duckdb`/`.sqlite` — прямо в базу.
4. **Строка без перевода строки — это путь или текст?** **Решение:** строка с переводом строки — текст; без перевода — всегда адрес; нет такого — `SOURCE_NOT_FOUND` с `action` «Pass format='text'…»; список строк — текст.
5. **Читать ли по URL** (CSV по http, ссылка «опубликовать» Google)? S3? **Решение:** http(s) — да (вкл. «опубликовать» Google), S3 — нет.
6. **Чтение нескольких листов Excel или нескольких файлов сразу** (папка, маска `*.csv` — как «Объединить CSV» в надстройке)? **Решение:** маска `*.csv` и папка `dir/` → одна таблица + колонка `_source`; `book.xlsx#*` → все листы + колонка `_sheet`; разные колонки — объединение, пустые ячейки.

### C. Типы и значения
7. **Как обходиться с типами?** «NA», «null», «nan» как слова; ведущие нули (телефоны, ID). **Решение:** «NA», «null», «nan», «None», «-» — строки; пустая ячейка → `None`/`NA`, при записи → пустая ячейка; полностью пустые строки (и пустые строки в txt) пропускаются. Числа и даты угадываются, но колонка остаётся текстом, если есть ведущий ноль (`007`, `+7…`) или больше 15 цифр. `as_text=True` / `--as-text` — всё строки; `dtypes={...}` / `--dtype col=int` — вручную. Excel — типы ячеек как есть, с тем же правилом ведущих нулей.
8. **Как назвать колонку при чтении txt и списка строк?** **Решение:** txt и список строк — `text`; CSV — первая строка шапка, `header=False` / `--no-header` → `col1, col2, …`; `{col: [..]}` — ключи-колонки, `{k: v}` — `key`, `value`; `Series` — её имя или `value`; пустые и повторные имена чинятся (`col3`, `phrase_2`) с предупреждением в `warnings`.

### D. Форматы
9. **CSV при чтении:** определять кодировку (UTF-8, UTF-8-BOM, cp1251) и разделитель (`, ; \t |`)? **Решение:** кодировка `utf-8-sig` → `utf-8` → `cp1251`, вручную `encoding=` / `--encoding`; разделитель по первым 64 КБ из `, ; \t |`, вручную `sep=` / `--sep`; `.tsv` — всегда `\t`; найденное — в ответе (п. 28).
10. **CSV при записи:** UTF-8 или UTF-8-BOM (чтобы Excel открывал кириллицу)? Разделитель `,` или `;`? **Решение:** UTF-8 без BOM, `,`, `\n`; `profile="excel"` / `--profile excel` — UTF-8-BOM и `;`; `encoding`, `sep` — вручную.
11. **Excel при записи:** в существующую книгу — заменить лист, остальные сохранить? Оформление (ширина, жирная шапка)? **Решение:** пишем только `.xlsx` (xls/xlsb/ods — только чтение, запись → `FORMAT_UNSUPPORTED`); в существующей книге заменить лист, остальные сохранить, предупреждение, если есть графики/сводные; автоширина, закреплённая шапка, автофильтр; > 1 048 576 строк → `WRITE_FAILED` с `action` «csv или parquet»; лист по умолчанию `Sheet1`.
12. **JSON:** вложенный JSON раскладывать в колонки (`json_normalize`)? Форма записи — records? **Решение:** читаем массив записей, объект колонок, jsonl; вложенные объекты — `json_normalize` (`user.name`), вложенные списки — JSON-строкой; пишем records, `ensure_ascii=False`, `indent=2`; jsonl — запись на строку; даты ISO.
13. **Parquet:** через DuckDB (без тяжёлого pyarrow) или через pyarrow? **Решение:** через DuckDB, без pyarrow.
14. **stdin и stdout:** формат по умолчанию? **Решение:** чтение — по содержимому (`[`/`{` → JSON/jsonl, устойчивый разделитель → CSV, иначе текст); запись — CSV, одна колонка → текст, `--format` вручную; `--json` + цель `-` → данные в конверте как `"data": [records]`.

### E. Базы
15. **SQLite и DuckDB:** читать таблицу и запрос; писать с режимами заменить, дописать, ошибка. Нужно ли что-то ещё (Postgres, MySQL)? **Решение:** только SQLite (stdlib) и DuckDB. Адрес `x.sqlite#t`, `x.duckdb#t` (`.sqlite`, `.sqlite3`, `.db`, `.duckdb`; `.db` — по сигнатуре файла). Чтение: таблица (`#` / `table=`) или `query=` в базу; одна таблица — читаем её, несколько без указания → `SOURCE_NOT_FOUND` со списком. Запись: `mode=replace|append|error` / `--mode` — общий для всех целей, по умолчанию `replace`; одна транзакция; типы INTEGER/REAL/TEXT/TIMESTAMP; `append` с лишними колонками → `WRITE_FAILED` (схему не меняем), недостающие → NULL. Без PK, индексов, upsert в v1. Postgres/MySQL — позже через SQLAlchemy.

### F. Google Sheets
16. **Как хранить ключ сервисного аккаунта?** Путь к JSON-файлу (`~/Work/credentials/google_service_account.json`) или содержимое в keychain? **Решение:** порядок: `credentials=` / `--credentials PATH` → `DATAIO_GOOGLE_CREDENTIALS` (путь) → `GOOGLE_APPLICATION_CREDENTIALS` → keychain (`dataio auth login google --file key.json`) → конфиг `google.credentials_path`. Нет ключа → `AUTH_REQUIRED` с `action`. `auth status` показывает источник и email сервисного аккаунта; 403 → `AUTH_REQUIRED` с `action` «Share the sheet with <sa-email> as Editor».
17. **Режимы записи:** заменить лист, дописать строки, писать с ячейки (`A5`)? Создавать лист, если его нет? **Решение:** `replace|append|error`; нет листа — создать; `start="A5"` / `--start A5`; `replace` чистит только значения, оформление остаётся; запись `RAW` (вручную `value_input="user"`); новые Google Таблицы не создаём.
18. **Перезапись Google Таблицы — необратимое действие снаружи.** По стандарту нужны `--dry-run` и подтверждение. Делать так? **Решение:** подтверждение только для `replace` непустого листа. CLI: вопрос, `--confirm`, `--non-interactive` без `--confirm` → ошибка, `--dry-run` — что заменится. Библиотека: нужен `overwrite=True`, иначе `TARGET_EXISTS` с `action`. `append` и пустой лист — без подтверждения.
19. **Большие таблицы:** запись пачками (лимиты API)? **Решение:** пачки по 10 000 строк; 429 и 5xx — повтор с растущей паузой; > 10 млн ячеек — ошибка до записи с `action`; читаем отображаемые значения, далее правила типов из блока C.

### G. Общее поведение
20. **Режим записи по умолчанию для файлов:** перезаписать или ошибка, если файл есть? **Решение:** `replace` по умолчанию: файл целиком, лист/таблица — только они; атомарная запись (временный файл + переименование); `mode=error` → `TARGET_EXISTS`; `append`: csv/jsonl/txt — дописать (сверка шапки CSV), лист xlsx — ниже, json/parquet — прочитать + склеить + переписать. Защита — блок L.
21. **Что возвращает `write()`?** Описание цели (`{"target", "rows", "columns"}`) или объект для целей в памяти (`format="records"`, `"list"`, `"text"`)? **Решение:** цель-адрес → отчёт `{"target": {uri, format, mode, rows, columns}, "warnings": [...]}` (как у CLI); без цели → объект: `write(df, format="records")` → `list[dict]`, также `"list"`, `"dict"`, `"text"`, `"csv"`, `"json"`; типы через `@overload`.
22. **Большие файлы (сотни МБ):** потоковое чтение или чтение целиком? **Решение:** v1 — целиком; `query=` по csv/parquet DuckDB выполняет прямо по файлу; потоки — позже.
23. **Команды CLI в первой версии:** `convert`, `info` (строки, колонки, превью), `formats`? **Решение:** `convert`, `info`, `formats`, `backups`, `restore` + стандартные команды шаблона; `limit=` / `--limit N` — первые N строк.

### H. Процесс
24. **Релизы без Antagor.** По стандарту tools релиз делает `antagor publish`. Как теперь: ты ставишь тег руками, или я готовлю тег и отчёт для корневого агента `tools`? **Решение:** через Antagor, режим `fast`; доставка — `antagor publish` (Человек). Версии `0.x`: ломающее — minor, остальное — patch.
25. **Порядок работы:** TDD с красным коммитом первым (стандарт tools) — оставляем? **Решение:** да, TDD с красным коммитом первым.

### I. Ответ и ошибки (для агента)
26. **Ошибки библиотеки и CLI — одни.** **Решение:** `read()`/`write()` бросают `DataioError(code, message, action)` — подкласс `CliError`; CLI превращает в стандартный конверт (`cli-generator/skills/cli-builder/reference/conventions.md`).
27. **Свои коды.** **Решение:** `SOURCE_NOT_FOUND` (2), `FORMAT_UNKNOWN` (2), `FORMAT_UNSUPPORTED` (2), `TARGET_EXISTS` (1), `READ_FAILED` (1), `WRITE_FAILED` (1); Google/http — стандартные `AUTH_REQUIRED` (3), `PROVIDER_ERROR` (5). В `message` — адрес и причина, в `action` — что сделать (например, список имеющихся листов).
28. **Ответ `convert --json`.** **Решение:** `{"ok": true, "source": {uri, format, encoding, delimiter, rows, columns}, "target": {uri, format, mode, rows}, "warnings": [...]}`; всё угаданное — в ответе. `--dry-run` — тот же ответ без записи.
29. **`info --json`.** **Решение:** формат, строки, колонки с типами, превью 5 строк, список листов/таблиц.

### J. Массовые операции
30. **Объединение.** **Решение:** маска `'in/*.csv'`, `'in/**/*.xlsx'`, папка, список адресов `read([...])`, в CLI несколько `IN`; `'reports/*.xlsx#*'` — все листы всех книг; колонки `_source`, `_sheet` (отключить `source_column=None` / `--no-source-column`); разная структура — объединение колонок + предупреждение; `strict=True` / `--strict` → `SCHEMA_MISMATCH` (2) с колонками по файлам.
31. **Разбиение.** **Решение:** шаблон в адресе цели: `out/{region}.csv` + `split_by="region"`; `book.xlsx#{region}` — по листам (и в Google); `out/part_{n}.csv` + `chunk_rows=10000`; недопустимые символы в именах заменяются; `drop_split_column=True` убирает колонку.
32. **Пакетная конвертация 1:1.** **Решение:** `dataio convert 'in/*.csv' 'out/{stem}.xlsx'` — каждый файл отдельно.
33. **Ответ и ошибки пакета.** **Решение:** `targets: [{uri, rows}, …]` + итог; по умолчанию стоп на первой ошибке; `keep_going=True` / `--keep-going` — собирать `errors: [{uri, code, message}]`, при любой ошибке `ok: false`; `--dry-run` — список того, что будет создано.
34. **Паритет.** **Решение:** в библиотеке `convert(src, dst, **opts)`, CLI `convert` вызывает её.

### K. Стандарт имён
35. **Функции и команды.** **Решение:** `read(source, **opts)` → DataFrame (CLI `dataio convert SRC -`); `write(df, target, **opts)` → отчёт; `convert(source, target, **opts)` → отчёт (CLI `dataio convert SRC DST`); `info(source, **opts)` (CLI `dataio info SRC`); `formats()` (CLI `dataio formats`) — форматы, что умеют, их параметры.
36. **Правило параметров.** **Решение:** флаг = имя параметра, `_` → `-`; bool → `--flag`, при умолчании `True` → `--no-flag`; dict → повторяемый флаг (`--dtype a=int`); исключений нет (`fmt` переименован в `format`).
37. **Общий словарь.** **Решение:** `format`, `sheet`, `table`, `query`, `encoding`, `sep`, `header`, `as_text`, `dtypes`, `mode`, `start`, `split_by`, `chunk_rows`, `credentials`; `mode` везде `replace|append|error`; шаблоны `{колонка}`, `{n}`, `{stem}`; служебные колонки с `_`.
38. **Конфликт имён в `convert`.** **Решение:** общие для обеих сторон (`format`, `sheet`, `table`, `encoding`, `sep`, `header`, `credentials`) — с префиксом `in_`/`out_` (`--in-encoding`, `--out-sep`); остальные без префикса; в `read()`/`write()` префиксов нет.
39. **Паритет проверяет тест.** **Решение:** тест сверяет сигнатуры функций и флаги CLI.

### L. Защита от потери данных
40. **Резервная копия перед перезаписью.** **Решение:** перед `replace` существующего файла, листа, таблицы, листа Google и перед `append` в json/parquet; в `~/.local/share/dataio/backups/<время>_<id>/` + описание (что, куда, когда, строки); Google и базы — прежние значения в parquet; хранить 50 последних, до 14 дней, до 2 ГБ; объект > 500 МБ — без копии, с предупреждением; `backup=False` / `--no-backup`.
41. **Откат.** **Решение:** `dataio backups` (`--json`), `dataio restore [ID]` (без ID — последняя; текущее состояние сначала тоже в копию); в библиотеке `backups()`, `restore(id)`.
42. **Явное разрешение.** **Решение:** без `overwrite=True` / `--confirm` → `TARGET_EXISTS`, если цель = источник или `replace` непустого листа Google.
43. **Предупреждения.** **Решение:** в `warnings` — резкое уменьшение строк («replacing 10 000 rows with 12») и пропавшие колонки.
44. **`--dry-run`.** **Решение:** по каждой цели `exists`, `rows_before`, `rows_after`. Локальные файлы — без вопросов (копия спасает).

### M. Стандарт CLI (cli-builder)
45. **Ключ Google.** **Решение:** провайдер `google` в `credentials/manager`; порядок: `--credentials` → `DATAIO_GOOGLE_*` → keychain → `GOOGLE_APPLICATION_CREDENTIALS` (`legacy_env`); путь в конфиге убран (секреты не из конфига); `health_check()` для `auth status --check`; ошибки gspread → `AuthRequired` / `ProviderError`. Заменяет п. 16 в части конфига.
46. **http(s).** **Решение:** провайдер на `HttpProvider` (повторы, таймауты, коды — из шаблона).
47. **Резервные копии.** **Решение:** в user data dir через `platformdirs`, объявлены в `DATA_FILES` (`describe --json`).
48. **Опасные операции.** **Решение:** `require_confirmation` + `--dry-run` для `convert` (замена непустого листа Google) и `restore`; отмечены в `SKILL.md`.
49. **Команды.** **Решение:** `convert`, `info`, `formats`, `backups`, `restore` рядом со стандартными; заглушка `run` удаляется; dataio работает без проекта, `.rb_dataio/config.toml` — только умолчания проекта (например, `csv.profile`).
50. **Документация.** **Решение:** help и сообщения на английском, `Example:` в каждой команде; список команд — только в help; CHANGELOG — из заголовков задач.
51. **Контракты.** **Решение:** semkit кладёт `tests/contracts/semkit/dataio.yaml` (через dev), гейт его проверяет.
52. **Тестовые швы.** **Решение:** (1) публичный API библиотеки — основное поведение; (2) CLI `--json` через `CliRunner` — конверт, коды выхода, `--dry-run`/`--confirm`, паритет флагов, плюс шаблонные снапшоты help, `describe`, `auth status`; (3) контракты потребителей. Google и http — подменённый клиент, без сети.

---
