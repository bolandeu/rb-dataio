"""Shared fixtures."""

from __future__ import annotations

from pathlib import Path

import platformdirs
import pytest


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
