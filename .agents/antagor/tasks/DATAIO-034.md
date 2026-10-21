---
id: DATAIO-034
title: 'doctor is healthy on a server with env credentials: no false failure for the
  keychain, the provider or a missing project'
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
type: bugfix
owns_paths:
- src/rb_dataio/commands/doctor.py
- src/rb_dataio/credentials/health.py
- tests/test_cli.py
- tests/test_auth.py
test_paths:
- tests/test_cli.py
- tests/test_auth.py
docs: none
tools: []
worker_args: null
class: standard
decision: false
visual: null
depends_on: []
budget_usd: null
epic: null
spec_refs: []
checks:
- uv run pytest --no-cov tests/test_cli.py tests/test_auth.py
resident: null
tool: null
pr: null
translation: 'Ошибка от сисадмина (IDEA-323): на homeserver с ключами из переменных
  окружения dataio doctor ложно говорит healthy=false: нет связки ключей ОС, проверяется
  несуществующий провайдер ''default'', нет проекта. Исправление по согласованию с
  cli-generator: проверка credential следует правилу auth status, отсутствие связки
  ключей и проекта — не ошибка, сломанный проект — по-прежнему ошибка, имена проверок
  не меняются.'
---

Bug from sysadmin (IDEA-323): on homeserver (dataio 0.1.28, user rbtools, keys from Doppler env, no OS keychain)
`dataio auth status` is ok (google: env, unchecked), but `dataio doctor` reports `healthy: false`:

- `credential_store`: fails, because there is no keychain backend;
- `credential`: checks a provider named `default` ("run 'dataio auth login --provider default'"), and that provider
  does not exist; dataio's provider is `google`;
- `project`: fails outside a project, although dataio works without one.

A Windmill worker runs `dataio doctor` through rb-run, so agents read a false failure.
Repro on the Mac: `cd /tmp; DATAIO_GOOGLE_CLIENT_EMAIL=a@b.c DATAIO_GOOGLE_PRIVATE_KEY=x dataio doctor --json`.

## The rule (agreed with cli-generator; its template gets the same fix)

1. `credential` follows the `auth status` rule (`credentials/health.py`, `status()` / `is_problem()`): ok when each
   required provider is `ok` or `unchecked` and none is `invalid` or `expired`. `detail` names the providers and their
   source (env, keychain, missing), never a value. No check names a `default` provider.
2. `credential_store`: no keychain backend is reported, not failed (`ok: true`, detail: no OS keychain, credentials
   come from environment variables). The keychain is only a dev override (the Standard, Credentials and providers).
3. `project`: no project is reported, not failed (`ok: true`, detail: no project; dataio works without one). A
   project that is there but broken (`config`, `cli_compat`) still fails, as now.
4. Keep the check names and their order (`python`, `cli_version`, `project`, …, `credential_store`, `credential`):
   the `--json` shape does not change.

## Tests

Tests first, through the CLI under `--json` (`invoke_json`), with env credentials and no keychain (the tests already
fake the keyring: see `fake_keyring` in tests/test_auth.py; a backend that is not there must be possible too).
`tests/test_cli.py::test_doctor_json` asserts `healthy is False  # no project here`: the requirement changed;
it asserts the new rule instead. Put the reason in the report.

## Acceptance

- Given DATAIO_GOOGLE_CLIENT_EMAIL and DATAIO_GOOGLE_PRIVATE_KEY in env, no OS keychain backend and no project, When `dataio doctor --json` runs, Then healthy is true and credential_store, credential and project are ok with a detail [check: tests/test_auth.py]
- Given a required provider whose credential is invalid or expired, When `dataio doctor --json` runs, Then the credential check is not ok and names that provider [check: tests/test_auth.py]
- Given a project whose config.toml does not parse, When `dataio doctor --json` runs, Then the config check still fails [check: tests/test_cli.py]
- Given any case, When `dataio doctor --json` runs, Then no check names a provider 'default' and the check names stay the same [check: tests/test_cli.py]

## How to test

Seam 2, the CLI under --json through CliRunner (invoke_json); env credentials by monkeypatch.setenv; the keyring backend faked or absent (fake_keyring of tests/test_auth.py); no network.

## Basis

auth status already has the rule: src/rb_dataio/credentials/health.py status() and is_problem(). Reuse them in doctor; do not copy the rule.

## Read first

- `src/rb_dataio/credentials/manager.py`
- `src/rb_dataio/providers/__init__.py`

## Out of scope

- auth status and its report shape
- the health checks with --check (network calls): doctor does not call providers
- new check names or a new --json field
