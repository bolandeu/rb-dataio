"""The backup store: the old content of each replaced target, kept so that `restore` can bring it back.

One folder per entry in the user data dir: the old content under the target's file name
and `entry.json` (the `Backup`). The entry file comes last and in one step, so a listing
never sees half an entry, and two processes never share a folder. The old content is a
hard link when the store and the target share a file system (the write then puts a new
file in the target's place and the old one stays as it was), a copy otherwise.
Limits (data/settings.toml): entries, age and total size; a target over the object limit
is not kept, with a warning.
"""

from __future__ import annotations

import math
import os
import secrets
import shutil
import time
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import platformdirs

from ..._distribution import TOOL
from ..data_files import BACKUP_DIR
from ..errors import BackupNotFound
from .protection import TargetState, write_atomically
from .report import Backup
from .settings import settings

ENTRY = "entry.json"
MB = 2**20
DAY = 86_400  # seconds


def _store() -> Path:
    return platformdirs.user_data_path(TOOL) / BACKUP_DIR


def content(entry: Backup) -> Path:
    """The file that holds the old content of `entry`."""
    return _store() / entry.id / Path(entry.target).name


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


@contextmanager
def kept(path: Path, format_name: str, before: TargetState, uri: str) -> Generator[list[str]]:
    """Keep a backup of what `path` holds for the write inside; a failed write drops it again.

    Yields the warnings: a target over the object limit is not kept.
    """
    limit = settings().backup.max_object_mb
    size = path.stat().st_size
    if size > limit * MB:
        yield [f"no backup of '{uri}': it is {math.ceil(size / MB)} MB, over the {limit} MB limit"]
        return
    entry = _keep(path, format_name, before)
    try:
        yield []
    except BaseException:
        shutil.rmtree(_store() / entry.id, ignore_errors=True)
        raise
    _prune()


def _keep(path: Path, format_name: str, before: TargetState) -> Backup:
    now = datetime.fromtimestamp(time.time(), UTC)
    entry = Backup(
        id=f"{now:%Y%m%d-%H%M%S}-{secrets.token_hex(4)}",  # unique even for many writes a second
        time=now.isoformat(timespec="microseconds"),
        target=str(path.absolute()),
        format=format_name,
        rows=before.rows,
        columns=before.columns,
    )
    folder = _store() / entry.id
    folder.mkdir(parents=True)
    try:
        os.link(path, content(entry))
    except OSError:  # another file system, or one without hard links
        shutil.copyfile(path, content(entry))
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
