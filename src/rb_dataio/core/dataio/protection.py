"""Protection of a target around a write: safety checks, the backup, the atomic write.

Hooks for now: no warnings, no backup, a direct write. The protection task fills them
(target equals source, row drop and lost columns, the backup store, temporary file and rename).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pandas as pd

from .options import WriteOptions


def check_safety(frame: pd.DataFrame, path: Path, options: WriteOptions) -> list[str]:
    """The warnings about this write; raises when the write must not happen."""
    return []


def keep_backup(path: Path, options: WriteOptions) -> None:
    """Save what `path` holds now, so that `restore` can bring it back."""


def write_atomically(path: Path, write: Callable[[Path], None]) -> None:
    write(path)
