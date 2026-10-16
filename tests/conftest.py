"""Shared fixtures."""

from __future__ import annotations

from pathlib import Path

import platformdirs
import pytest

from rb_dataio.core.dataio.options import ReadOptions
from rb_dataio.credentials import manager as credentials
from rb_dataio.formats import Loaded, TextAdapter


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The user data dir of dataio moved into a temporary folder, for this process and the processes it starts.

    platformdirs finds it from HOME on macOS and from XDG_DATA_HOME on Linux, so both point inside tmp_path.
    """
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_DATA_HOME", str(home / ".local" / "share"))
    path = platformdirs.user_data_path("dataio")
    assert path.is_relative_to(home)
    return path


@pytest.fixture
def reads(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    """The paths the text adapters were asked to read, in order."""
    paths: list[Path] = []
    original = TextAdapter.read

    def counting(self: TextAdapter, path: Path, options: ReadOptions) -> Loaded:
        paths.append(path)
        return original(self, path, options)

    monkeypatch.setattr(TextAdapter, "read", counting)
    return paths


@pytest.fixture
def fake_keyring(monkeypatch: pytest.MonkeyPatch):
    """In-memory stand-in for the OS keychain so auth tests don't touch it."""
    store: dict[tuple[str, str], str] = {}

    def fake_set_password(service: str, username: str, password: str) -> None:
        store[(service, username)] = password

    def fake_get_password(service: str, username: str) -> str | None:
        return store.get((service, username))

    def fake_delete_password(service: str, username: str) -> None:
        store.pop((service, username), None)

    monkeypatch.setattr(credentials.keyring, "set_password", fake_set_password)
    monkeypatch.setattr(credentials.keyring, "get_password", fake_get_password)
    monkeypatch.setattr(credentials.keyring, "delete_password", fake_delete_password)
    return store
