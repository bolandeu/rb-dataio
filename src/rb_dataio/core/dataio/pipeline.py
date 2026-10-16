"""The read and the write pipelines.

    read:    resolve the source -> adapter read (of the part, in a container) -> value normalisation -> limit
    write:   resolve the target -> dry run -> safety checks -> backup -> atomic write -> report

A write to a container (containers.py) starts from a copy of the current file and changes
only its part, so the backup and the atomic write are of the whole file.
    restore: find the backup -> dry run -> backup of the current content -> atomic write -> report

A source is an address, a text or a Python object (objects.py); a target is an address,
or none for `write()` to return the data. `-` is stdin or stdout (stdio.py); local paths
are the files; the other schemes are recognised and refused with FORMAT_UNSUPPORTED until their tasks.
`refuse_over_source` stops `convert` before it reads a source that is also its target.
"""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Callable
from contextlib import nullcontext
from pathlib import Path
from typing import Any, cast

import pandas as pd

from ...formats import ContainerAdapter, FormatAdapter, Loaded, WriteRefused
from ...formats import txt as txt_format
from ..errors import DataioError, FormatUnsupported, ReadFailed, SourceNotFound, TargetExists, WriteFailed
from . import backup, containers, objects, protection, registry, stdio, values
from .address import FILE, STDIO, Address, parse
from .options import Mode, ReadOptions, SharedOptions, WriteOptions
from .protection import MISSING, TargetState
from .report import Info, PlannedTarget, Report, SourcePart, TargetPart, column_names

PREVIEW_ROWS = 5  # the first rows `info()` shows
IN_MEMORY = "<object>"  # how a report and an error name the target of `write()` with none


def _address(text: str, options: SharedOptions) -> Address:
    address = parse(text, sheet=options.sheet, table=options.table)
    if address.scheme not in (FILE, STDIO):
        raise FormatUnsupported(
            f"'{text}': addresses of the scheme '{address.scheme}' are not supported in this release.",
            action="Pass the path of a local file or -.",
        )
    return address


def _unable(format_name: str, ability: str, instead: str | None = None) -> FormatUnsupported:
    """The refusal of an ability; `instead` is the format of the same kind that has it."""
    return FormatUnsupported(
        f"Format '{format_name}' cannot {ability} in this release.",
        action=f"Use {instead} instead: it is the format of this kind that can {ability}."
        if instead
        else f"Pick a format that can {ability}: formats() lists them.",
    )


def read_frame(source: object, options: ReadOptions) -> tuple[pd.DataFrame, SourcePart, list[str]]:
    """The table, the source part of the report and the warnings of the read."""
    uri = _source_name(source)
    try:
        format_name, loaded = _load(source, options)
        frame, normalised = values.normalise(loaded.frame, options, infer=loaded.infers_types)
    except (ValueError, OSError) as exc:  # pandas parse and decode errors are ValueErrors
        raise ReadFailed(uri, exc) from exc
    if options.limit is not None:
        frame = frame.head(options.limit)
    part = SourcePart(
        uri=uri,
        format=format_name,
        encoding=loaded.encoding,
        delimiter=loaded.delimiter,
        rows=len(frame),
        columns=column_names(frame),
    )
    return frame, part, [*loaded.warnings, *normalised]


def _source_name(source: object) -> str:
    """How the report and the errors name a source: its address, else `<text>` or the kind of the object."""
    if isinstance(source, str) and "\n" in source:
        return "<text>"
    if isinstance(source, str | os.PathLike):
        return os.fspath(source)
    return f"<{type(source).__name__}>"


def _load(source: object, options: ReadOptions) -> tuple[str, Loaded]:
    """The format name and the table of a source."""
    if not isinstance(source, str | os.PathLike):
        return type(source).__name__, objects.loaded(source)
    text = os.fspath(source)
    if objects.is_text(text, options):
        return registry.TEXT, txt_format.ADAPTER.parse(text, options)
    address = _address(text, options)
    if address.scheme == STDIO:
        return stdio.read(options)
    path = Path(address.path)
    if not path.exists():
        raise SourceNotFound(text)
    adapter = registry.resolve(address, options.format)
    if not adapter.reads:
        raise _unable(adapter.name, "read")
    if isinstance(adapter, ContainerAdapter):
        return adapter.name, containers.read(adapter, path, address.fragment, options, text)
    return adapter.name, adapter.read(path, options)


def refuse_over_source(source: str, target: str, options: WriteOptions) -> None:
    """Raise WriteOverSource when `convert` would write over its own source; called before the source is read."""
    if not options.dry_run:
        protection.check_over_source(_address(target, options), parse(source), options.overwrite)


def write_frame(frame: pd.DataFrame, target: str, options: WriteOptions) -> Report:
    """Write `frame` to `target`."""
    address = _address(target, options)
    if address.scheme == STDIO:
        return _write_stdout(frame, target, options)
    path = Path(address.path)
    adapter = registry.resolve(address, options.format)
    if not adapter.writes:
        raise _unable(adapter.name, "write", adapter.written_as)
    if options.mode is Mode.APPEND and not adapter.appends:
        raise _unable(adapter.name, "append")
    if options.mode is Mode.ERROR and path.exists():
        raise TargetExists(target)
    keep = options.backup and options.mode is Mode.REPLACE
    before = _state(target, path, options)
    part = TargetPart(uri=target, format=adapter.name, mode=options.mode, rows=len(frame), columns=column_names(frame))
    if options.dry_run:
        return Report(target=_planned(part, before))
    write, written = _writer(adapter, frame, address, options)
    warnings = protection.loss_warnings(frame, before, options.mode)
    from_copy = options.mode is Mode.APPEND or isinstance(adapter, ContainerAdapter)
    warnings += _replace(path, part, before, write, keep=keep, from_copy=from_copy)
    return Report(target=part, warnings=[*warnings, *written])


def _writer(
    adapter: FormatAdapter, frame: pd.DataFrame, address: Address, options: WriteOptions
) -> tuple[Callable[[Path], object], list[str]]:
    """The write of `frame` into a file, and the list that gets the warnings of the adapter once it ran."""
    if not isinstance(adapter, ContainerAdapter):
        return (lambda into: adapter.write(frame, into, options)), []
    part = containers.part_to_write(adapter, Path(address.path), address.fragment)
    written: list[str] = []
    return (lambda into: written.extend(adapter.write_part(frame, into, part, options))), written


def frame_data(frame: pd.DataFrame, options: WriteOptions) -> Any:
    """`frame` as the object or the text of `format=` (records when none): `write()` with no target."""
    try:
        return objects.rendered(frame, options.format or objects.RECORDS, options, IN_MEMORY)
    except ValueError as exc:
        raise WriteFailed(IN_MEMORY, exc) from exc


def _write_stdout(frame: pd.DataFrame, target: str, options: WriteOptions) -> Report:
    format_name = stdio.format_of(frame, options)
    part = TargetPart(uri=target, format=format_name, mode=options.mode, rows=len(frame), columns=column_names(frame))
    if options.dry_run:
        return Report(target=_planned(part, MISSING))
    try:
        data = stdio.write(frame, format_name, options)
    except ValueError as exc:
        raise WriteFailed(target, exc) from exc
    return Report(target=part, data=data)


def restore_target(backup_id: str | None, dry_run: bool) -> Report:
    """Put the content of a backup back in its target, after a backup of what the target holds now."""
    entry = backup.find(backup_id)
    path = Path(entry.target)
    reading = SharedOptions(format=entry.format, sheet=None, table=None, encoding=None, sep=None, header=True)
    before = _state(entry.target, path, reading)
    part = TargetPart(uri=entry.target, format=entry.format, mode=Mode.REPLACE, rows=entry.rows, columns=entry.columns)
    if dry_run:
        return Report(target=_planned(part, before), backup=entry)
    warnings = _replace(
        path, part, before, lambda into: shutil.copyfile(backup.content(entry), into), keep=True, from_copy=False
    )
    return Report(target=part, backup=entry, warnings=warnings)


def _state(target: str, path: Path, options: SharedOptions) -> TargetState:
    """What the target holds now, read with the options of the write.

    The rows and the columns are not read (None) when the target is over the backup size limit.
    """
    if not path.exists():
        return MISSING
    if backup.over_limit(path, target):
        return TargetState(exists=True, rows=None, columns=None)
    try:
        frame, _, _ = read_frame(target, ReadOptions.reading_back(options))
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
    path: Path,
    part: TargetPart,
    before: TargetState,
    write: Callable[[Path], object],
    *,
    keep: bool,
    from_copy: bool,
) -> list[str]:
    """Write the target atomically, with `keep` after a backup of what it holds; the warnings of the backup.

    `from_copy`: `write` gets a copy of the current file to change (an append, a part of a container).
    """
    keeping = backup.kept(path, part.format, before, part.uri) if keep and before.exists else nullcontext([])
    try:
        with keeping as warnings:
            protection.write_atomically(path, write, from_copy=from_copy)
    except (ValueError, OSError) as exc:
        raise WriteFailed(part.uri, exc, action=exc.action if isinstance(exc, WriteRefused) else None) from exc
    return warnings


def describe_source(source: str, options: ReadOptions) -> Info:
    frame, part, _ = read_frame(source, options)
    # to_json: missing values become null and dates ISO strings; without a path it returns the text
    preview = cast(str, frame.head(PREVIEW_ROWS).to_json(orient="records", force_ascii=False, date_format="iso"))
    return Info(
        source=part,
        parts=_parts(source, options),
        types={str(column): str(dtype) for column, dtype in frame.dtypes.items()},
        preview=json.loads(preview),
    )


def _parts(source: str, options: ReadOptions) -> list[str]:
    """The parts of a container file; none for any other source."""
    if objects.is_text(source, options):
        return []
    address = _address(source, options)
    if address.scheme != FILE:
        return []
    adapter = registry.resolve(address, options.format)
    return adapter.parts(Path(address.path)) if isinstance(adapter, ContainerAdapter) else []
