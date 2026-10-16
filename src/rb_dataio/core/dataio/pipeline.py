"""The read and the write pipelines.

    read:    resolve the source -> adapter read (of the part, in a container) -> query= -> value normalisation -> limit
    write:   resolve the target -> dry run -> safety checks -> backup -> atomic write -> report

A write to a container (containers.py) starts from a copy of the current file and changes
only its part, so the backup and the atomic write are of the whole file. A base (a
`BaseAdapter`) is written in place instead, in its one transaction: the file is not
copied, and the backup holds the old rows of the table only.
    restore: find the backup -> dry run -> backup of the current content -> atomic write -> report
(of a table: a write of its old rows to it). `query=` (query.py) runs on the file itself
when its format can, else over the table read.

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
from contextlib import AbstractContextManager, nullcontext
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pandas as pd

from ...formats import BaseAdapter, ContainerAdapter, FormatAdapter, Loaded, WriteRefused
from ...formats import txt as txt_format
from ..errors import DataioError, FormatUnsupported, ReadFailed, SourceNotFound, TargetExists, WriteFailed
from . import backup, containers, objects, protection, query, registry, stdio, values
from .address import FILE, STDIO, Address, parse
from .options import Mode, ReadOptions, SharedOptions, WriteOptions
from .protection import MISSING, TargetState
from .report import Backup, Info, PlannedTarget, Report, SourcePart, TargetPart, column_names

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
    """The format name and the table of a source; under `query=` the result of the query."""
    if not isinstance(source, str | os.PathLike):
        return type(source).__name__, query.over_table(objects.loaded(source), options)
    text = os.fspath(source)
    if objects.is_text(text, options):
        return registry.TEXT, query.over_table(txt_format.ADAPTER.parse(text, options), options)
    address = _address(text, options)
    if address.scheme == STDIO:
        format_name, loaded = stdio.read(options)
        return format_name, query.over_table(loaded, options)
    return _load_file(address, options)


def _load_file(address: Address, options: ReadOptions) -> tuple[str, Loaded]:
    path = Path(address.path)
    if not path.exists():
        raise SourceNotFound(address.text)
    adapter = registry.resolve(address, options.format)
    if not adapter.reads:
        raise _unable(adapter.name, "read")
    if options.query and (result := adapter.query(path, options.query, options)) is not None:
        return adapter.name, result
    if isinstance(adapter, ContainerAdapter):
        loaded = containers.read(adapter, path, address.fragment, options, address.text)
    else:
        loaded = adapter.read(path, options)
    return adapter.name, query.over_table(loaded, options)


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
    part = TargetPart(uri=target, format=adapter.name, mode=options.mode, rows=len(frame), columns=column_names(frame))
    if isinstance(adapter, BaseAdapter):
        return _write_table(adapter, frame, address, part, options)
    keep = options.backup and options.mode is Mode.REPLACE
    before = _state(target, path, options)
    if options.dry_run:
        return Report(target=_planned(part, before))
    write, written = _writer(adapter, frame, address, options)
    warnings = protection.loss_warnings(frame, before, options.mode)
    from_copy = options.mode is Mode.APPEND or isinstance(adapter, ContainerAdapter)
    warnings += _replace(path, part, before, write, keep=keep, from_copy=from_copy)
    return Report(target=part, warnings=[*warnings, *written])


def _write_table(
    adapter: BaseAdapter, frame: pd.DataFrame, address: Address, part: TargetPart, options: WriteOptions
) -> Report:
    """Write a table of a base in place, in the adapter's one transaction, after a backup of its old rows only."""
    path = Path(address.path)
    table = containers.part_to_write(adapter, path, address.fragment)
    old = _old_rows(adapter, path, table, options, part.uri)
    before = MISSING if old is None else TargetState(exists=True, rows=len(old), columns=column_names(old))
    if options.dry_run:
        return Report(target=_planned(part, before))
    keeping = (
        backup.kept_rows(old, path, adapter.name, table, part.uri)
        if old is not None and options.backup and options.mode is Mode.REPLACE
        else nullcontext([])
    )
    written: list[str] = []
    warnings = _written(part.uri, keeping, lambda: written.extend(adapter.write_part(frame, path, table, options)))
    return Report(target=part, warnings=[*protection.loss_warnings(frame, before, options.mode), *warnings, *written])


def _old_rows(adapter: BaseAdapter, path: Path, table: str, options: WriteOptions, uri: str) -> pd.DataFrame | None:
    """The rows the table holds now, as the base stores them; None when the base has no such table."""
    try:
        if not path.exists() or table not in adapter.parts(path):
            return None
        return adapter.read_part(path, table, ReadOptions.reading_back(options)).frame
    except (ValueError, OSError) as exc:
        raise WriteFailed(uri, exc) from exc


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
    if entry.table is not None:
        return _restore_table(entry, dry_run)
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


def _restore_table(entry: Backup, dry_run: bool) -> Report:
    """Put the old rows of a table back: a replace of the table with them, which keeps its current rows first."""
    options = WriteOptions(
        format=entry.format,
        sheet=None,
        table=entry.table,
        encoding=None,
        sep=None,
        header=True,
        mode=Mode.REPLACE,
        profile=None,
        overwrite=False,
        backup=True,
        dry_run=dry_run,
    )
    return write_frame(backup.rows(entry), entry.target, options).model_copy(update={"backup": entry})


def _state(target: str, path: Path, options: SharedOptions) -> TargetState:
    """What the target holds now, read with the options of the write.

    The rows and the columns are not read (None) when the target is over the backup size limit.
    """
    if not path.exists():
        return MISSING
    if backup.over_limit(path.stat().st_size, target):
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
    return _written(part.uri, keeping, lambda: protection.write_atomically(path, write, from_copy=from_copy))


def _written(uri: str, keeping: AbstractContextManager[list[str]], write: Callable[[], object]) -> list[str]:
    """Run `write` with the backup `keeping` (or none) and return its warnings; a failed write is WRITE_FAILED."""
    try:
        with keeping as warnings:
            write()
    except (ValueError, OSError) as exc:
        raise WriteFailed(uri, exc, action=exc.action if isinstance(exc, WriteRefused) else None) from exc
    return warnings


def describe_source(source: str, options: ReadOptions) -> Info:
    options, part_rows = _described_table(source, options)
    frame, part, _ = read_frame(source, options)
    # to_json: missing values become null and dates ISO strings; without a path it returns the text
    preview = cast(str, frame.head(PREVIEW_ROWS).to_json(orient="records", force_ascii=False, date_format="iso"))
    return Info(
        source=part,
        parts=_parts(source, options),
        part_rows=part_rows,
        types={str(column): str(dtype) for column, dtype in frame.dtypes.items()},
        preview=json.loads(preview),
    )


def _file_adapter(source: str, options: ReadOptions) -> tuple[FormatAdapter, Address] | None:
    """The adapter and the address of a source that is an existing local file; None for any other source."""
    if objects.is_text(source, options):
        return None
    address = _address(source, options)
    if address.scheme != FILE or not Path(address.path).exists():
        return None
    return registry.resolve(address, options.format), address


def _parts(source: str, options: ReadOptions) -> list[str]:
    """The parts of a container file; none for any other source."""
    found = _file_adapter(source, options)
    if found is None or not isinstance(found[0], ContainerAdapter):
        return []
    return found[0].parts(Path(found[1].path))


def _described_table(source: str, options: ReadOptions) -> tuple[ReadOptions, dict[str, int]]:
    """The rows of every table of a base; with several tables and none named, `options` name the first to describe."""
    found = _file_adapter(source, options)
    if found is None:
        return options, {}
    adapter, address = found
    if not isinstance(adapter, BaseAdapter):
        return options, {}
    counts = adapter.row_counts(Path(address.path))
    if address.fragment is None and len(counts) > 1:
        options = replace(options, table=next(iter(counts)))
    return options, counts
