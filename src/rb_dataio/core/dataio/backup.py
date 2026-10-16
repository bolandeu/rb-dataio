"""The backup store: the old content of each replaced target, kept so that `restore` can bring it back.

One folder per entry in the user data dir: the old content under a fixed name (`content`; entries made before it keep the target's file name)
and `entry.json` (the `Backup`). The entry file comes last and in one step, so a listing
never sees half an entry, and two processes never share a folder. The old content is
always a real copy, so an in-place edit of the target never reaches it. For a table of a
base (`kept_rows`) it is the old rows of that table only, as parquet; `rows` reads them back.
Limits (data/settings.toml): entries, age and total size; a target over the object limit
is not kept, with a warning.
"""

from __future__ import annotations

import math
import secrets
import shutil
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import platformdirs

from ..._distribution import TOOL
from ...formats import parquet
from ..data_files import BACKUP_DIR
from ..errors import BackupNotFound
from .protection import TargetState, write_atomically
from .report import Backup, column_names
from .settings import settings

ENTRY = "entry.json"
CONTENT = "content"
MB = 2**20
DAY = 86_400  # seconds


def _store() -> Path:
    return platformdirs.user_data_path(TOOL) / BACKUP_DIR


def content(entry: Backup) -> Path:
    """The file that holds the old content of `entry`; older entries keep it under the target's file name."""
    fixed = _store() / entry.id / CONTENT
    return fixed if fixed.exists() else fixed.with_name(Path(entry.target).name)


def entries() -> list[Backup]:
    """The kept backups, newest first."""
    found = []
    for file in _store().glob(f"*/{ENTRY}"):
        try:
            found.append(Backup.model_validate_json(file.read_text(encoding="utf-8")))
        except FileNotFoundError:  # another process pruned it meanwhile
            continue
    return sorted(found, key=lambda entry: entry.time, reverse=True)


def find(backup_id: str | None) -> Backup:
    """The backup `backup_id`, the newest without one."""
    kept = entries()
    for entry in kept:
        if backup_id is None or entry.id == backup_id:
            return entry
    raise BackupNotFound(backup_id, [entry.id for entry in kept])


def over_limit(size: int, uri: str) -> str | None:
    """The warning for a target of `size` bytes over the object limit, else None."""
    limit = settings().backup.max_object_mb
    if size <= limit * MB:
        return None
    return f"no backup of '{uri}': it is {math.ceil(size / MB)} MB, over the {limit} MB limit"


@contextmanager
def kept(path: Path, format_name: str, before: TargetState, uri: str) -> Generator[list[str]]:
    """Keep a backup of what `path` holds for the write inside; a failed write drops it again.

    Yields the warnings: a target over the object limit (only its size is read) is not kept.
    """
    if warning := over_limit(path.stat().st_size, uri):
        yield [warning]
        return
    with _kept(_keep(path, format_name, before, lambda into: shutil.copy2(path, into))):
        yield []


@contextmanager
def kept_rows(rows: pd.DataFrame, path: Path, format_name: str, table: str, uri: str) -> Generator[list[str]]:
    """Keep the old `rows` of the table `table` of the base `path`, as parquet, for the write inside.

    Yields the warnings: rows over the object limit (by their size in memory) are not kept.
    """
    if warning := over_limit(int(rows.memory_usage(deep=True).sum()), uri):
        yield [warning]
        return
    before = TargetState(exists=True, rows=len(rows), columns=column_names(rows))
    with _kept(_keep(path, format_name, before, lambda into: parquet.write_file(rows, into), table=table)):
        yield []


def rows(entry: Backup) -> pd.DataFrame:
    """The old rows of the table that `entry` keeps."""
    return parquet.read_file(content(entry))


@contextmanager
def _kept(entry: Backup) -> Generator[None]:
    """The write inside runs with `entry` kept: a failed write drops it again, a done one prunes the store."""
    try:
        yield
    except BaseException:
        shutil.rmtree(_store() / entry.id, ignore_errors=True)
        raise
    _prune()


def _keep(
    path: Path, format_name: str, before: TargetState, fill: Callable[[Path], object], table: str | None = None
) -> Backup:
    """A new entry for the target `path`; `fill` writes its old content into the file it gets."""
    now = datetime.fromtimestamp(time.time(), UTC)
    entry = Backup(
        id=f"{now:%Y%m%d-%H%M%S}-{secrets.token_hex(4)}",  # unique even for many writes a second
        time=now.isoformat(timespec="microseconds"),
        target=str(path.absolute()),
        format=format_name,
        rows=before.rows,
        columns=before.columns,
        table=table,
    )
    folder = _store() / entry.id
    folder.mkdir(parents=True)
    fill(folder / CONTENT)
    write_atomically(folder / ENTRY, lambda into: into.write_text(entry.model_dump_json(), encoding="utf-8"))
    return entry


def _prune() -> None:
    """Remove the oldest entries beyond the count, the age or the total size limit."""
    limits = settings().backup
    oldest = time.time() - limits.max_age_days * DAY
    total = 0
    for number, entry in enumerate(entries()):
        try:
            total += content(entry).stat().st_size
        except FileNotFoundError:  # another process pruned it meanwhile
            continue
        too_old = datetime.fromisoformat(entry.time).timestamp() < oldest
        if number >= limits.max_entries or too_old or total > limits.max_total_mb * MB:
            shutil.rmtree(_store() / entry.id, ignore_errors=True)
