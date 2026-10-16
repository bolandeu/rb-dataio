"""The read and the write pipelines.

    read:    resolve the address -> adapter read -> value normalisation -> limit
    write:   resolve the target -> dry run -> safety checks -> backup -> atomic write -> report
    restore: find the backup -> dry run -> backup of the current content -> atomic write -> report

Only local paths resolve in this release; `-` and the other schemes are recognised
and refused with FORMAT_UNSUPPORTED until their tasks.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from contextlib import nullcontext
from pathlib import Path
from typing import cast

import pandas as pd

from ..errors import DataioError, FormatUnsupported, ReadFailed, SourceNotFound, TargetExists, WriteFailed
from . import backup, protection, registry, values
from .address import FILE, Address, parse
from .options import Mode, ReadOptions, SharedOptions, WriteOptions
from .protection import MISSING, TargetState
from .report import Info, PlannedTarget, Report, SourcePart, TargetPart, column_names

PREVIEW_ROWS = 5  # the first rows `info()` shows


def _local(text: str, options: SharedOptions) -> tuple[Address, Path]:
    address = parse(text, sheet=options.sheet, table=options.table)
    if address.scheme != FILE:
        raise FormatUnsupported(
            f"'{text}': addresses of the scheme '{address.scheme}' are not supported in this release.",
            action="Pass the path of a local file.",
        )
    return address, Path(address.path)


def _unable(format_name: str, ability: str) -> FormatUnsupported:
    return FormatUnsupported(
        f"Format '{format_name}' cannot {ability} in this release.",
        action=f"Pick a format that can {ability}: formats() lists them.",
    )


def read_frame(source: str, options: ReadOptions) -> tuple[pd.DataFrame, SourcePart]:
    address, path = _local(source, options)
    if not path.exists():
        raise SourceNotFound(source)
    adapter = registry.resolve(address, options.format)
    if not adapter.reads:
        raise _unable(adapter.name, "read")
    try:
        loaded = adapter.read(path, options)
    except (ValueError, OSError) as exc:  # pandas parse and decode errors are ValueErrors
        raise ReadFailed(source, exc) from exc
    frame = values.normalise(loaded.frame, options)
    if options.limit is not None:
        frame = frame.head(options.limit)
    part = SourcePart(
        uri=source,
        format=adapter.name,
        encoding=loaded.encoding,
        delimiter=loaded.delimiter,
        rows=len(frame),
        columns=column_names(frame),
    )
    return frame, part


def write_frame(frame: pd.DataFrame, target: str, options: WriteOptions, source: str | None = None) -> Report:
    """Write `frame` to `target`; `source` is the address `convert` read, so a write over it is caught."""
    address, path = _local(target, options)
    adapter = registry.resolve(address, options.format)
    if not adapter.writes:
        raise _unable(adapter.name, "write")
    if options.mode is Mode.APPEND and not adapter.appends:
        raise _unable(adapter.name, "append")
    if options.mode is Mode.ERROR and path.exists():
        raise TargetExists(target)
    before = _state(target, path, options)
    part = TargetPart(uri=target, format=adapter.name, mode=options.mode, rows=len(frame), columns=column_names(frame))
    if options.dry_run:
        return Report(target=_planned(part, before))
    protection.check_over_source(address, parse(source) if source else None, options.overwrite)
    warnings = protection.loss_warnings(frame, before, options.mode)
    warnings += _replace(
        path,
        part,
        before,
        lambda into: adapter.write(frame, into, options),
        keep=options.backup and options.mode is Mode.REPLACE,
    )
    return Report(target=part, warnings=warnings)


def restore_target(backup_id: str | None, dry_run: bool) -> Report:
    """Put the content of a backup back in its target, after a backup of what the target holds now."""
    entry = backup.find(backup_id)
    path = Path(entry.target)
    reading = SharedOptions(format=entry.format, sheet=None, table=None, encoding=None, sep=None, header=True)
    before = _state(entry.target, path, reading)
    part = TargetPart(uri=entry.target, format=entry.format, mode=Mode.REPLACE, rows=entry.rows, columns=entry.columns)
    if dry_run:
        return Report(target=_planned(part, before), backup=entry)
    warnings = _replace(path, part, before, lambda into: shutil.copyfile(backup.content(entry), into), keep=True)
    return Report(target=part, backup=entry, warnings=warnings)


def _state(target: str, path: Path, options: SharedOptions) -> TargetState:
    """What the target holds now, read with the options of the write."""
    if not path.exists():
        return MISSING
    try:
        frame, _ = read_frame(target, ReadOptions.reading_back(options))
    except DataioError:  # not a table dataio can read: it is still replaced and kept
        return TargetState(exists=True, rows=None, columns=None)
    return TargetState(exists=True, rows=len(frame), columns=column_names(frame))


def _planned(part: TargetPart, before: TargetState) -> PlannedTarget:
    if part.mode is Mode.APPEND:
        after = None if before.rows is None or part.rows is None else before.rows + part.rows
    else:
        after = part.rows
    return PlannedTarget(**part.model_dump(), exists=before.exists, rows_before=before.rows, rows_after=after)


def _replace(
    path: Path, part: TargetPart, before: TargetState, write: Callable[[Path], object], *, keep: bool
) -> list[str]:
    """Write the target atomically, with `keep` after a backup of what it holds; the warnings of the backup."""
    keeping = backup.kept(path, part.format, before, part.uri) if keep and before.exists else nullcontext([])
    try:
        with keeping as warnings:
            protection.write_atomically(path, write, append=part.mode is Mode.APPEND)
    except (ValueError, OSError) as exc:
        raise WriteFailed(part.uri, exc) from exc
    return warnings


def describe_source(source: str, options: ReadOptions) -> Info:
    frame, part = read_frame(source, options)
    # to_json: missing values become null and dates ISO strings; without a path it returns the text
    preview = cast(str, frame.head(PREVIEW_ROWS).to_json(orient="records", force_ascii=False, date_format="iso"))
    return Info(
        source=part,
        types={str(column): str(dtype) for column, dtype in frame.dtypes.items()},
        preview=json.loads(preview),
    )
