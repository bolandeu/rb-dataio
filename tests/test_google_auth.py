"""The google key: where it is found, AUTH_REQUIRED without it, and its entry in `auth status --check`.

The key is the fields of a service-account key file. The places, in order: the key file of
`credentials=` / `--credentials`, the env vars DATAIO_GOOGLE_*, the keychain and the key file
that GOOGLE_APPLICATION_CREDENTIALS names. The token request of the health check is replaced
with a fake client: no test uses the network.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

import pytest
from google.auth import exceptions as google_errors

from rb_dataio.core.errors import AuthRequired, CliError
from rb_dataio.credentials import manager as credentials
from rb_dataio.providers import google
from rb_dataio.providers.google import GoogleProvider

from .test_auth import ENTRY_KEYS, by_provider
from .test_cli import invoke

ENV_EMAIL, ENV_KEY = "DATAIO_GOOGLE_CLIENT_EMAIL", "DATAIO_GOOGLE_PRIVATE_KEY"
KEY_FILE_ENV = "GOOGLE_APPLICATION_CREDENTIALS"


def account(place: str) -> dict[str, str]:
    return {"client_email": f"{place}@demo.iam.gserviceaccount.com", "private_key": f"key-of-{place}"}


def key_file(path: Path, place: str) -> Path:
    """A service-account key file as Google gives it: more fields than the key needs."""
    path.write_text(json.dumps({"type": "service_account", "project_id": "demo", **account(place)}), encoding="utf-8")
    return path


@pytest.fixture
def no_key(monkeypatch: pytest.MonkeyPatch, fake_keyring: dict) -> dict:
    """No place holds a google key: the env of the machine that runs the tests is cleared."""
    for name in (ENV_EMAIL, ENV_KEY, KEY_FILE_ENV):
        monkeypatch.delenv(name, raising=False)
    return fake_keyring


@pytest.fixture
def tokens(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, float]]:
    """The fake client: it grants every token request and records the account and the timeout of each."""
    asked: list[tuple[str, float]] = []

    def authorise(service_account: Mapping[str, str], timeout: float) -> None:
        asked.append((service_account["client_email"], timeout))

    monkeypatch.setattr(google, "authorise", authorise)
    return asked


def email(provider: GoogleProvider) -> str:
    return provider.service_account()["client_email"]


# --- the order of the places ------------------------------------------------------


def test_each_place_wins_over_the_ones_after_it(no_key: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    flag = key_file(tmp_path / "flag.json", "flag")
    monkeypatch.setenv(ENV_EMAIL, account("env")["client_email"])
    monkeypatch.setenv(ENV_KEY, account("env")["private_key"])
    credentials.store_credential("google", account("keychain"))
    monkeypatch.setenv(KEY_FILE_ENV, str(key_file(tmp_path / "legacy.json", "legacy")))

    assert GoogleProvider(key_file=str(flag)).service_account() == account("flag")
    assert GoogleProvider().service_account() == account("env")
    monkeypatch.delenv(ENV_EMAIL)
    monkeypatch.delenv(ENV_KEY)
    assert email(GoogleProvider()) == "keychain@demo.iam.gserviceaccount.com"
    credentials.delete_credential("google")
    assert GoogleProvider().service_account() == account("legacy")


def test_no_key_anywhere_is_auth_required_with_the_login(no_key: dict) -> None:
    with pytest.raises(AuthRequired) as caught:
        GoogleProvider().service_account()
    assert (caught.value.code, caught.value.exit_code) == ("AUTH_REQUIRED", 3)
    assert caught.value.action == "Run 'dataio auth login --provider google --credentials <key.json>'."


def test_a_key_file_that_cannot_be_read_is_auth_required_naming_it(no_key: dict, tmp_path: Path) -> None:
    (tmp_path / "list.json").write_text("[1, 2]", encoding="utf-8")
    for name in ("missing.json", "list.json"):
        with pytest.raises(CliError) as caught:
            GoogleProvider(key_file=str(tmp_path / name)).service_account()
        assert (caught.value.code, caught.value.exit_code) == ("AUTH_REQUIRED", 3)
        assert f"'{tmp_path / name}'" in caught.value.message


def test_login_stores_the_fields_of_a_key_file(no_key: dict, tmp_path: Path) -> None:
    path = key_file(tmp_path / "key.json", "login")
    result = invoke("auth", "login", "--provider", "google", "--credentials", str(path), "--non-interactive", "--json")
    assert result.exit_code == 0, result.output
    assert json.loads(no_key[("dataio:google", "google")]) == account("login")
    assert GoogleProvider().service_account() == account("login")


def test_login_refuses_a_key_file_without_a_field_the_provider_needs(no_key: dict, tmp_path: Path) -> None:
    path = tmp_path / "key.json"
    path.write_text(json.dumps({"client_email": "a@demo.iam.gserviceaccount.com"}), encoding="utf-8")
    result = invoke("auth", "login", "--provider", "google", "--credentials", str(path), "--json")
    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["message"] == f"The key file '{path}' has no private_key."
    assert no_key == {}


# --- auth status ------------------------------------------------------------------


def status(*args: str, env: dict[str, str] | None = None) -> tuple[int, dict, str]:
    result = invoke("auth", "status", "--provider", "google", *args, "--json", env=env)
    return result.exit_code, by_provider(json.loads(result.stdout))["google"], result.output


def test_check_shows_the_source_the_status_and_the_email(no_key: dict, tokens: list, tmp_path: Path) -> None:
    path = key_file(tmp_path / "key.json", "file")
    code, entry, printed = status("--check", env={KEY_FILE_ENV: str(path)})
    assert list(entry) == ENTRY_KEYS
    assert (code, entry["source"], entry["status"]) == (0, "file", "ok")
    assert entry["source_ref"] == f"key file {path} ({KEY_FILE_ENV})"
    assert entry["message"] == "service account file@demo.iam.gserviceaccount.com"
    assert tokens == [("file@demo.iam.gserviceaccount.com", 10.0)]
    assert "key-of-file" not in printed


def test_the_env_key_is_reported_as_env(no_key: dict, tokens: list) -> None:
    code, entry, _ = status("--check", env={ENV_EMAIL: "env@demo.iam.gserviceaccount.com", ENV_KEY: "key-of-env"})
    assert (code, entry["source"], entry["source_ref"], entry["status"]) == (0, "env", f"{ENV_EMAIL}, {ENV_KEY}", "ok")


def test_google_is_optional_and_missing_without_a_key(no_key: dict) -> None:
    code, entry, _ = status()
    assert (code, entry["required"], entry["status"]) == (0, False, "missing")
    assert entry["fields"] == ["client_email", "private_key"]
    assert entry["source_ref"].endswith(f"or the key file that {KEY_FILE_ENV} names")


@pytest.mark.parametrize(
    ("refusal", "expected"),
    [  # a wrong key is a problem even for an optional provider; no answer is not
        (google_errors.RefreshError("invalid_grant: account not found"), (3, "invalid")),
        (google_errors.TransportError("connection refused"), (0, "unreachable")),
    ],
)
def test_a_refused_token_is_invalid_and_no_answer_unreachable(
    no_key: dict, monkeypatch: pytest.MonkeyPatch, refusal: Exception, expected: tuple[int, str]
) -> None:
    def authorise(service_account: Mapping[str, str], timeout: float) -> None:
        raise refusal

    monkeypatch.setattr(google, "authorise", authorise)
    code, entry, _ = status("--check", env={ENV_EMAIL: "a@demo.iam.gserviceaccount.com", ENV_KEY: "key"})
    assert (code, entry["status"]) == expected


def test_a_malformed_private_key_is_invalid_before_any_request(no_key: dict) -> None:
    code, entry, printed = status("--check", env={ENV_EMAIL: "a@demo.iam.gserviceaccount.com", ENV_KEY: "not-a-pem"})
    assert (code, entry["status"]) == (3, "invalid")
    assert "not-a-pem" not in printed
