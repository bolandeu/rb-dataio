"""Shared fixtures."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import platformdirs
import pytest
import typer.rich_utils

from rb_dataio.core.dataio.options import ReadOptions
from rb_dataio.credentials import manager as credentials
from rb_dataio.formats import Loaded, TextAdapter
from rb_dataio.output import human

# Typer reads these once, at import, and then forces terminal output — what a CI runner sets.
CI_ENV = {"GITHUB_ACTIONS": "true", "FORCE_COLOR": "1", "PY_COLORS": "1"}


@pytest.fixture(autouse=True)
def _plain_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """Typer and our Rich consoles force terminal output (colour, ANSI codes) when CI_ENV is set; the tests compare plain text.

    Both read the variables once, at import, so the value they stored is reset here.
    """
    monkeypatch.setattr(typer.rich_utils, "FORCE_TERMINAL", False)
    for console in (human.console, human.err_console):
        monkeypatch.setattr(console, "_force_terminal", False)
        monkeypatch.setattr(console, "_color_system", None)


@pytest.fixture
def same_in_ci(request: pytest.FixtureRequest) -> Callable[[str], None]:
    """Rerun this file's tests matching `-k` under CI_ENV in a fresh interpreter: the only way to set a value read at import."""
    if request.config.getoption("--snapshot-update", default=False):
        pytest.skip("the snapshots are being written; there is nothing to compare yet")

    def run(selection: str) -> None:
        options = ["-k", selection, "-p", "no:cacheprovider", "--no-cov", "-q"]
        command = [sys.executable, "-m", "pytest", str(request.path), *options]
        env = {**os.environ, **CI_ENV}
        result = subprocess.run(command, env=env, capture_output=True, text=True, check=False)  # noqa: S603
        assert result.returncode == 0, result.stdout[-3000:]

    return run


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
