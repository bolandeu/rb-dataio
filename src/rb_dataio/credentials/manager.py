"""Where a provider's credential fields are found, stored and removed.

A credential is a small bag of named fields per provider. It is found field by field in env vars
(`<NAMESPACE>_<PROVIDER>_<FIELD>`), the OS keychain, a legacy env var and a key file (`Lookup`: the places besides
env and keychain; `locate_fields` for the order), so secrets never live in a project file.

The keychain, the env-var convention, the stored-names index and the "read once, warn once" state live in the
shared `rb-credentials`; what stays here is dataio's own layer — the key file (JSON) and the `Lookup` that says
where else to look — plus the error mapping.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import keyring  # патч-цель тестов (`dataio.credentials.manager.keyring.*`)
from rb_credentials import Store, StoreUnavailable

from ..core.errors import CredentialStoreUnavailable, KeyFileUnreadable
from ..core.version import cli_name

if TYPE_CHECKING:
    from ..providers import Provider

log = logging.getLogger(__name__)

# Everything this CLI stores or reads lives under its namespace — the command name (`cli_name`), not the Python
# package: keychain service "<namespace>:<provider>", env vars <NAMESPACE>_<PROVIDER>_<FIELD>. Another tool's
# namespace can be read too (`Provider.shared_namespaces`), never written.
NAMESPACE = cli_name()

# A store per (shared namespaces, keyring module): the tests replace the module, and the store's
# "warn once" state must live between calls of the same one.
_CACHE: dict[tuple[tuple[str, ...], int], Store] = {}
_warned_missing = False


def _store(shared_namespaces: tuple[str, ...] = ()) -> Store:
    key = (shared_namespaces, id(keyring))
    if key not in _CACHE:
        _CACHE[key] = Store(NAMESPACE, shared_namespaces=shared_namespaces, keyring=keyring)
    return _CACHE[key]


def _service_name(provider: str, namespace: str = NAMESPACE) -> str:
    return Store(namespace).service_name(provider)


def _env_var_name(provider: str, field: str, namespace: str = NAMESPACE) -> str:
    return Store(namespace).env_var_name(provider, field)


def env_var_name(provider: str, field: str, namespace: str = NAMESPACE) -> str:
    return _env_var_name(provider, field, namespace)


def keychain_service(provider: str, namespace: str = NAMESPACE) -> str:
    return _service_name(provider, namespace)


def stored_names() -> list[str]:
    """Names of the credentials stored in the keychain by this CLI (env-only ones are not listed)."""
    return _store().stored_names()


def read_fields_from_env(provider: str, fields: list[str]) -> dict[str, str]:
    """Read whichever of `fields` are set as env vars for this provider."""
    return _store().read_from_env(provider, fields)


@dataclass(frozen=True)
class Lookup:
    """Where else a provider's fields may be: the `Provider` attributes of the same names.

    `key_file`: a key file (JSON) passed for this one call (`--credentials`); it alone gives
    the fields. `key_file_env`: an env var that names a key file, looked up last.
    """

    legacy_env: dict[str, str] | None = None
    legacy_env_first: bool = False
    shared_namespaces: tuple[str, ...] = ()
    key_file: str | None = None
    key_file_env: str | None = None

    @classmethod
    def of(cls, provider: Provider | type[Provider]) -> Lookup:
        """The places a provider (or its class, which passes no key file) declares."""
        return cls(
            legacy_env=provider.legacy_env,
            legacy_env_first=provider.legacy_env_first,
            shared_namespaces=provider.shared_namespaces,
            key_file=provider.key_file,
            key_file_env=provider.key_file_env,
        )


def get_credential(
    provider: str, *, env_fields: list[str] | None = None, lookup: Lookup | None = None
) -> dict[str, str] | None:
    """Resolve the full credential bag for a provider.

    Env vars win field-by-field over what's stored in the keychain, so CI can override a single field (a rotated
    token) without touching the rest. `env_fields` lets a multi-field provider declare its field names explicitly,
    so env vars are checked even before anything has ever been stored. `lookup` holds the other places (see
    `locate_fields` for the order); providers call `Provider.credential()`.
    """
    lookup = lookup or Lookup()
    if lookup.key_file:
        return read_key_file(lookup.key_file) or None
    store = _store(lookup.shared_namespaces)
    stored = store.stored(provider)
    fields = env_fields or list(stored) or ["api_key"]
    located = _locate(store, provider, fields, lookup)
    merged = {**stored, **{field: value for field, (value, _, _) in located.items()}}
    return merged or None


def locate_fields(provider: str, fields: list[str], *, lookup: Lookup | None = None) -> dict[str, tuple[str, str, str]]:
    """Map each present field to (value, source "env" | "keychain" | "file", where: the env var, service or file).

    Order per field, first hit wins:
    1. env var `<NAMESPACE>_<PROVIDER>_<FIELD>`, then the same for each shared namespace;
    2. keychain `<namespace>:<provider>`, own namespace first, then shared ones;
    3. the field's legacy env var (`legacy_env`) — or right after 1 with `legacy_env_first`;
    4. the key file that `key_file_env` names.
    For `auth status`, which reports the source and must never print the value.
    """
    lookup = lookup or Lookup()
    return _locate(_store(lookup.shared_namespaces), provider, fields, lookup)


def _locate(store: Store, provider: str, fields: list[str], lookup: Lookup) -> dict[str, tuple[str, str, str]]:
    located = dict(
        store.locate(
            provider,
            fields,
            legacy_env=lookup.legacy_env,
            legacy_env_first=lookup.legacy_env_first,
        )
    )
    located |= _from_key_file_env([field for field in fields if field not in located], lookup.key_file_env)
    _warn_if_keychain_mattered(store, provider, [field for field in fields if field not in located])
    return located


def read_key_file(path: str) -> dict[str, str]:
    """The fields of a key file: a JSON object, as a service gives it (a Google service-account key)."""
    try:
        fields = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise KeyFileUnreadable(path, str(exc)) from exc
    if not isinstance(fields, dict):
        raise KeyFileUnreadable(path, "the key file is not a JSON object")
    return {str(name): str(value) for name, value in fields.items()}


def _from_key_file_env(missing: list[str], key_file_env: str | None) -> dict[str, tuple[str, str, str]]:
    """The `missing` fields from the key file that the env var `key_file_env` names, if it is set."""
    path = os.environ.get(key_file_env) if key_file_env and missing else None
    if path is None:
        return {}
    fields = read_key_file(path)
    where = f"{path} ({key_file_env})"
    return {field: (fields[field], "file", where) for field in missing if field in fields}


def _warn_if_keychain_mattered(store: Store, provider: str, missing: list[str]) -> None:
    global _warned_missing
    if missing and store.unavailable_reason is not None and not _warned_missing:
        _warned_missing = True
        log.warning(
            "OS credential store unavailable (%s) and %s not set in the environment for '%s'",
            store.unavailable_reason,
            ", ".join(missing),
            provider,
        )


def store_backend() -> str | None:
    """Name of the active keyring backend, or None when there's no usable one."""
    return _store().backend()


def store_credential(provider: str, fields: dict[str, str]) -> None:
    try:
        _store().store(provider, fields)
    except StoreUnavailable as exc:
        raise CredentialStoreUnavailable(provider, str(exc)) from exc


def delete_credential(provider: str) -> None:
    try:
        _store().delete(provider)
    except StoreUnavailable as exc:
        raise CredentialStoreUnavailable(provider, str(exc)) from exc


def get_secret(provider: str, field: str = "api_key") -> str | None:
    credential = get_credential(provider, env_fields=[field])
    return credential.get(field) if credential else None


def store_secret(provider: str, secret: str, field: str = "api_key") -> None:
    store_credential(provider, {field: secret})


def read_secret_from_env(provider: str, field: str = "api_key") -> str | None:
    return read_fields_from_env(provider, [field]).get(field)


def delete_secret(provider: str) -> None:
    delete_credential(provider)
