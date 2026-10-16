"""The google provider: the service-account key that Google Sheets are read and written with.

The key is the fields of a service-account key file (`client_email`, `private_key`), found in
this order: the key file passed as `credentials=` / `--credentials` (`GoogleProvider(key_file=...)`),
the env vars DATAIO_GOOGLE_*, the keychain (`auth login --provider google --credentials <key.json>`),
the key file that GOOGLE_APPLICATION_CREDENTIALS names. `service_account()` gives the fields or
AUTH_REQUIRED. `health_check()` is one token request through `authorise`, the one call to Google,
which tests replace (no network); its message names the email to share a sheet with.
`sheets()` is the gspread client of Google Sheets, made by `connect`, which tests replace too;
`call()` sends one request with it: again after a growing wait on 429 and 5xx, a 403 as
SheetNotShared (the email to share the sheet with), any other failure as PROVIDER_ERROR.
"""

from __future__ import annotations

import functools
import time
from collections.abc import Callable, Mapping
from http import HTTPStatus
from typing import TypeVar

import gspread
import requests
from google.auth import exceptions as google_errors
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from gspread.exceptions import APIError, SpreadsheetNotFound

from ..core.dataio.settings import settings
from ..core.errors import AuthRequired, CliError, ProviderError, SheetNotShared
from ..credentials.health import CHECK_TIMEOUT
from .base import Health, Provider

EMAIL = "client_email"
LOGIN_OPTIONS = "--credentials <key.json>"  # what `auth login --provider google` needs
# what a request to Google Sheets can fail with: the Sheets API, the key, the connection
_FAILURES = (APIError, PermissionError, SpreadsheetNotFound, google_errors.GoogleAuthError, requests.RequestException)
Answer = TypeVar("Answer")


def _signed(account: Mapping[str, str]) -> service_account.Credentials:
    """The credentials of the key; a malformed key is a ValueError, before any request."""
    endpoints = settings().google
    return service_account.Credentials.from_service_account_info(
        {**account, "token_uri": endpoints.token_uri}, scopes=endpoints.scopes
    )


def authorise(account: Mapping[str, str], timeout: float) -> None:
    """One token request signed with the key: Google grants it only to a real service account and a live key.

    A malformed key is a ValueError before any request; a refused one is a RefreshError.
    """
    _signed(account).refresh(functools.partial(Request(), timeout=timeout))


def connect(account: Mapping[str, str]) -> gspread.Client:
    """The gspread client signed with the key; it asks for a token at its first request."""
    client = gspread.authorize(_signed(account))
    client.set_timeout(settings().gsheet.timeout_seconds)
    return client


def _repeatable(exc: Exception) -> bool:
    """A 429 (too many requests) or a 5xx: Google said "not now", not "no"."""
    return isinstance(exc, APIError) and (exc.code == HTTPStatus.TOO_MANY_REQUESTS or exc.code >= 500)


class GoogleProvider(Provider):
    name = "google"
    credential_fields = (EMAIL, "private_key")
    public_fields = (EMAIL,)
    required = False  # dataio works without Google; only Google Sheets need the key
    key_file_env = "GOOGLE_APPLICATION_CREDENTIALS"

    def __init__(self, key_file: str | None = None) -> None:
        self.key_file = key_file

    def service_account(self) -> dict[str, str]:
        """The fields of the key; AUTH_REQUIRED with the way to log in when no place has them all."""
        account = self.credential() or {}
        if any(field not in account for field in self.credential_fields):
            raise AuthRequired(self.name, login_options=LOGIN_OPTIONS)
        return {field: account[field] for field in self.credential_fields}

    def health_check(self) -> Health:
        account = self.service_account()
        try:
            authorise(account, CHECK_TIMEOUT)
        except (ValueError, google_errors.GoogleAuthError) as exc:
            raise self._key_failure(exc) from exc
        return Health(message=f"service account {account[EMAIL]}")

    def sheets(self) -> gspread.Client:
        """The client of Google Sheets signed with the key."""
        account = self.service_account()
        try:
            return connect(account)
        except ValueError as exc:
            raise self._key_failure(exc) from exc

    def call(self, request: Callable[[], Answer], uri: str) -> Answer:
        """The answer of `request` to Google Sheets about the address `uri`.

        A 429 or a 5xx repeats it after a wait that doubles each time (data/settings.toml); after
        the last repeat it is PROVIDER_ERROR with the status, as any other failure is.
        """
        limits = settings().gsheet
        attempt = 0
        while True:
            try:
                return request()
            except _FAILURES as exc:
                if attempt >= limits.retries or not _repeatable(exc):
                    raise self._failure(exc, uri) from exc
            time.sleep(limits.backoff_seconds * 2**attempt)
            attempt += 1

    def _failure(self, exc: Exception, uri: str) -> CliError:
        """The error of a failed request about `uri`: a 403 names the email to share the sheet with."""
        if isinstance(exc, PermissionError) or (isinstance(exc, APIError) and exc.code == HTTPStatus.FORBIDDEN):
            return SheetNotShared(uri, self.service_account()[EMAIL])
        if isinstance(exc, SpreadsheetNotFound):
            return ProviderError(
                self.name,
                f"no spreadsheet at '{uri}'",
                status=HTTPStatus.NOT_FOUND,
                action="Check the spreadsheet id of the address: dataio does not create spreadsheets.",
            )
        if isinstance(exc, APIError):
            return ProviderError(self.name, f"HTTP {exc.code} for '{uri}': {exc.error['message']}", status=exc.code)
        if isinstance(exc, google_errors.GoogleAuthError):
            return self._key_failure(exc)
        return ProviderError(
            self.name,
            f"{type(exc).__name__} while calling Google Sheets for '{uri}'",
            action="Check the network connection, then retry.",
        )

    def _key_failure(self, exc: Exception) -> CliError:
        """A malformed or a refused key is AUTH_REQUIRED; no token for want of a connection, PROVIDER_ERROR."""
        if isinstance(exc, google_errors.TransportError):
            return ProviderError(self.name, f"no token from Google: {exc}")
        return AuthRequired(self.name, login_options=LOGIN_OPTIONS)
