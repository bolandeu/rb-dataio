"""The google provider: the service-account key that Google Sheets are read and written with.

The key is the fields of a service-account key file (`client_email`, `private_key`), found in
this order: the key file passed as `credentials=` / `--credentials` (`GoogleProvider(key_file=...)`),
the env vars DATAIO_GOOGLE_*, the keychain (`auth login --provider google --credentials <key.json>`),
the key file that GOOGLE_APPLICATION_CREDENTIALS names. `service_account()` gives the fields or
AUTH_REQUIRED. `health_check()` is one token request through `authorise`, the one call to Google,
which tests replace (no network); its message names the email to share a sheet with.
"""

from __future__ import annotations

import functools
from collections.abc import Mapping

from google.auth import exceptions as google_errors
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from ..core.dataio.settings import settings
from ..core.errors import AuthRequired, ProviderError
from ..credentials.health import CHECK_TIMEOUT
from .base import Health, Provider

EMAIL = "client_email"
LOGIN_OPTIONS = "--credentials <key.json>"  # what `auth login --provider google` needs


def authorise(account: Mapping[str, str], timeout: float) -> None:
    """One token request signed with the key: Google grants it only to a real service account and a live key.

    A malformed key is a ValueError before any request; a refused one is a RefreshError.
    """
    endpoints = settings().google
    key = service_account.Credentials.from_service_account_info(
        {**account, "token_uri": endpoints.token_uri}, scopes=endpoints.scopes
    )
    key.refresh(functools.partial(Request(), timeout=timeout))


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
        except (ValueError, google_errors.RefreshError) as exc:
            raise AuthRequired(self.name, login_options=LOGIN_OPTIONS) from exc
        except google_errors.TransportError as exc:
            raise ProviderError(self.name, f"no token from Google: {exc}") from exc
        return Health(message=f"service account {account[EMAIL]}")
