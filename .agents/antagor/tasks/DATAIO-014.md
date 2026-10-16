---
id: DATAIO-014
title: 'Remote sources in the core: the Google key and auth status, gsheet and http(s)
  addresses, start/value_input, confirmation for a non-empty remote part'
status: publish
attempts: 1
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
- src/rb_dataio/core/
- src/rb_dataio/commands/
- src/rb_dataio/credentials/
- src/rb_dataio/providers/
- src/rb_dataio/__init__.py
- src/rb_dataio/formats/__init__.py
- src/rb_dataio/data/
- tests/test_remote_core.py
- tests/test_google_auth.py
- tests/snapshots/
- tests/test_parity.py
- tests/test_auth.py
- pyproject.toml
- uv.lock
test_paths:
- tests/test_remote_core.py
- tests/test_google_auth.py
- tests/test_parity.py
- tests/test_auth.py
- tests/test_describe.py
- tests/conftest.py
docs: none
tools: []
worker_args: null
class: hard
decision: false
visual: null
depends_on:
- DATAIO-008
- DATAIO-011
- DATAIO-012
- DATAIO-013
budget_usd: null
epic: E-004
spec_refs: []
checks:
- python3 scripts/check_command_docstrings.py
- uv run scripts/release.py --check
resident: null
tool: null
pr: null
translation: 'Удалённые источники в ядре: провайдер google в слое ключей шаблона (порядок
  --credentials → DATAIO_GOOGLE_* → keychain → GOOGLE_APPLICATION_CREDENTIALS; нет
  — AUTH_REQUIRED), auth status с email сервисного аккаунта; разбор URL таблицы с
  gid и gsheet://id#Лист; http(s) идёт в адаптер, заявивший схему; новые параметры
  start и value_input (+ флаги, паритет); подтверждение замены непустой удалённой
  части (CLI спрашивает, --confirm, --non-interactive — отказ; библиотека — overwrite=True;
  --dry-run — rows_before/after). Проверка тестовыми адаптерами без сети.'
---

Google Sheets and http(s) links must read and write like files. This task builds what both need from the core and the template, so the Sheets and http formats only talk to their service.

The Google key: a google provider in the template credentials layer with a service-account field bag, resolved in the standard order (--credentials, DATAIO_GOOGLE_*, the keychain, GOOGLE_APPLICATION_CREDENTIALS); none found is AUTH_REQUIRED with the action to log in; 'dataio auth status --check' shows the google entry with source, status and the service-account email in the standard report shape; the health check is one cheap authorised call through an injectable client. Addresses: a Google Sheets browser URL (with gid) and gsheet://<id>#Sheet parse into the spreadsheet id and the sheet; http(s) URLs reach a format adapter that claims the scheme, instead of the current FORMAT_UNSUPPORTED. New parameters start (the top-left cell) and value_input ('raw' default, 'user') on write and convert (target side), with CLI flags and the parity test. Confirmation: a container adapter may declare that replacing a non-empty part needs confirmation; the CLI then asks through the template require_confirmation (--confirm skips, --non-interactive refuses), the library needs overwrite=True (else TARGET_EXISTS), and --dry-run reports rows_before and rows_after.

Proven with a remote container format and a scheme adapter that live only in the tests; no test uses the network.

## Acceptance

- Given the key in --credentials, DATAIO_GOOGLE_*, the keychain and GOOGLE_APPLICATION_CREDENTIALS at once, When the google key is resolved, Then --credentials wins; removing each in turn picks the next in that order; Given none, Then AUTH_REQUIRED with the action to log in [check: tests/test_google_auth.py]
- Given 'dataio auth status --check --json' with an injected client, When it runs, Then the google entry has source, status 'ok' and the service-account email in the template report shape [check: tests/test_google_auth.py]
- Given 'https://docs.google.com/spreadsheets/d/ID/edit#gid=123' and 'gsheet://ID#Sheet1', When parsed, Then the id is ID and the sheet is gid 123 or Sheet1 [check: tests/test_remote_core.py]
- Given an https URL and a test adapter claiming https, When read, Then that adapter reads it; Given no adapter for the scheme, Then FORMAT_UNSUPPORTED as before [check: tests/test_remote_core.py]
- Given write and convert, When compared with the CLI, Then start / --start and value_input / --value-input exist and the parity test passes [check: tests/test_parity.py]
- Given a test remote container with a non-empty part, When the CLI replaces it under --non-interactive without --confirm, Then it is refused; Given --confirm, Then it is replaced; Given --dry-run, Then the report has rows_before and rows_after and nothing changes; Given the library without overwrite=True, Then TARGET_EXISTS [check: tests/test_remote_core.py]

## How to test

Integration tests through the public library API and the CLI under --json; credentials through env and a fake keychain; a remote container and a scheme adapter defined in the tests with injected clients; no network.

## Basis

The template credentials and providers layers (Provider, health checks, auth status), output.require_confirmation; the container contract (DATAIO-008) and the base backups (DATAIO-011).

## Read first

- `docs/SPEC.md`
- `docs/adr/0004-stroka-vsegda-adres.md`
- `docs/adr/0005-rezervnaya-kopiya-vmesto-voprosov.md`
- `CODING_STANDARDS.md`

## Out of scope

- The real Google Sheets and http(s) formats; creating spreadsheets; OAuth user login; S3.

## Feedback

### Attempt 1: file docstring

- add a docstring to src/rb_dataio/credentials/manager.py: what it holds and why
- add a docstring to src/rb_dataio/providers/base.py: what it holds and why
