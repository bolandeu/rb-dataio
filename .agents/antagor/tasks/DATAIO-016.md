---
id: DATAIO-016
title: 'http(s) sources: CSV and JSON links, including Google ''Publish to web'',
  read directly'
status: done
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
- src/rb_dataio/formats/http.py
- tests/test_http_source.py
- tests/data/http/
- src/rb_dataio/core/dataio/pipeline.py
- src/rb_dataio/formats/__init__.py
test_paths:
- tests/test_http_source.py
- tests/test_frame.py
docs: none
tools: []
worker_args: null
class: standard
decision: false
visual: null
depends_on:
- DATAIO-014
budget_usd: null
epic: E-004
spec_refs: []
checks:
- python3 scripts/check_command_docstrings.py
- uv run scripts/release.py --check
resident: null
tool: null
pr: null
translation: 'http(s)-источники: CSV/JSON/jsonl по ссылке, включая «Опубликовать в
  интернете» Google (output=csv); формат по URL или Content-Type; разбор существующими
  парсерами с определением кодировки и разделителя; запросы через HttpProvider шаблона;
  404/ошибки/таймаут — PROVIDER_ERROR со статусом; запись — FORMAT_UNSUPPORTED. Тесты
  без сети.'
---

A user reads a table straight from an http(s) link. The format of the content comes from the URL (extension, Google 'Publish to web' output=csv) or from the response Content-Type, and the existing CSV, JSON and jsonl parsers read it, with the same encoding and delimiter detection and value rules as files. The request goes through the template HttpProvider (timeouts, retries, error mapping): 404, other HTTP errors and timeouts are PROVIDER_ERROR with the status. http(s) is read only.

## Acceptance

- Given an https URL ending in .csv served by an injected transport with a cp1251 ';' body, When read, Then the table has correct Cyrillic and the report has encoding cp1251 and delimiter ';' [check: tests/test_http_source.py]
- Given a Google 'Publish to web' link with output=csv, When read, Then it is read as CSV; Given a URL with no extension and Content-Type application/json, Then as JSON [check: tests/test_http_source.py]
- Given a 404 or a timeout from the transport, When read, Then PROVIDER_ERROR names the URL and the status (404) or the timeout [check: tests/test_http_source.py]
- Given write(df, 'https://example.com/a.csv'), When it runs, Then FORMAT_UNSUPPORTED says http(s) is read only [check: tests/test_http_source.py]
- Given 'dataio convert https://…/a.csv out.json --json' with the injected transport, When it runs, Then exit 0 and out.json has the rows [check: tests/test_http_source.py]

## How to test

Integration tests through the public library API and the CLI under --json with an injected HTTP transport (httpx MockTransport or the template's test seam); no network.

## Basis

The scheme routing of DATAIO-014; the template HttpProvider; the existing CSV/JSON text adapters (TextAdapter.load) for parsing.

## Read first

- `CODING_STANDARDS.md`

## Out of scope

- Writing over http; auth headers; S3; Google Sheets API.
