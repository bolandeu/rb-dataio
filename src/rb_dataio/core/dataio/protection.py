"""Protection of a target around a write: the write over the source, the loss warnings, the atomic write.

The backup itself is the backup store's (backup.py); the write pipeline puts the steps in order.
"""

from __future__ import annotations

import os
import secrets
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ..errors import WriteOverSource
from .address import Address
from .options import Mode
from .report import column_names
from .settings import settings


@dataclass(frozen=True)
class TargetState:
    """What a target holds before a write. A missing target has 0 rows; an unreadable one has rows None."""

    exists: bool
    rows: int | None
    columns: list[str] | None


MISSING = TargetState(exists=False, rows=0, columns=[])


def check_over_source(target: Address, source: Address | None, overwrite: bool) -> None:
    """Raise when the target is the source itself (the same file and the same sheet or table) and `overwrite` is off."""
    if source is None or overwrite or target.fragment != source.fragment:
        return
    try:
        same = os.path.samefile(target.path, source.path)
    except OSError:  # the target does not exist yet
        return
    if same:
        raise WriteOverSource(target.text)


def loss_warnings(frame: pd.DataFrame, before: TargetState, mode: Mode) -> list[str]:
    """The warnings of a replace that drops most rows or loses columns."""
    if mode is not Mode.REPLACE or before.rows is None or before.columns is None:
        return []
    warnings = []
    if len(frame) < before.rows * settings().warnings.row_drop_share:
        warnings.append(f"replacing {before.rows} rows with {len(frame)}")
    kept = set(column_names(frame))
    if lost := [column for column in before.columns if column not in kept]:
        warnings.append(f"columns lost: {', '.join(lost)}")
    return warnings


def write_atomically(path: Path, write: Callable[[Path], object], *, from_copy: bool = False) -> None:
    """`write` fills a temporary file next to `path`, which then replaces `path` in one step.

    A failed write leaves `path` as it was and removes the temporary file. With `from_copy`
    the temporary file starts as a copy of `path` (an append, a part of a container); the new file keeps the permissions of
    the old one. The name keeps the suffix, as some engines pick the format by it.
    """
    temporary = path.with_name(f".{path.stem}.{secrets.token_hex(4)}.tmp{path.suffix}")
    exists = path.exists()
    try:
        if from_copy and exists:
            shutil.copyfile(path, temporary)
        write(temporary)
        if exists:
            shutil.copymode(path, temporary)
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
