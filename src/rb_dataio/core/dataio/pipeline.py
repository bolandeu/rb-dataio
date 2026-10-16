"""The read and the write pipelines.

    read:  resolve the address -> adapter read -> value normalisation -> limit
    write: resolve the target -> dry run -> safety checks -> backup -> atomic write -> report

Only local paths resolve in this release; `-` and the other schemes are recognised
and refused with FORMAT_UNSUPPORTED until their tasks.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pandas as pd

from ..errors import FormatUnsupported, ReadFailed, SourceNotFound, TargetExists, WriteFailed
from . import protection, registry, values
from .address import FILE, Address, parse
from .options import Mode, ReadOptions, SharedOptions, WriteOptions
from .report import Info, Report, SourcePart, TargetPart, column_names

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


def read_frame(source: str, options: ReadOptions) -> tuple[pd.DataFrame, SourcePart, list[str]]:
    """The table, the source part of the report and the warnings of the read."""
    address, path = _local(source, options)
    if not path.exists():
        raise SourceNotFound(source)
    adapter = registry.resolve(address, options.format)
    if not adapter.reads:
        raise _unable(adapter.name, "read")
    try:
        loaded = adapter.read(path, options)
        frame, warnings = values.normalise(loaded.frame, options, infer=adapter.infers_types)
    except (ValueError, OSError) as exc:  # pandas parse and decode errors are ValueErrors
        raise ReadFailed(source, exc) from exc
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
    return frame, part, warnings


def write_frame(frame: pd.DataFrame, target: str, options: WriteOptions) -> Report:
    address, path = _local(target, options)
    adapter = registry.resolve(address, options.format)
    if not adapter.writes:
        raise _unable(adapter.name, "write")
    if options.mode is Mode.APPEND and not adapter.appends:
        raise _unable(adapter.name, "append")
    if options.mode is Mode.ERROR and path.exists():
        raise TargetExists(target)
    part = TargetPart(uri=target, format=adapter.name, mode=options.mode, rows=len(frame), columns=column_names(frame))
    if options.dry_run:
        return Report(target=part)
    warnings = protection.check_safety(frame, path, options)
    protection.keep_backup(path, options)
    try:
        protection.write_atomically(path, lambda into: adapter.write(frame, into, options))
    except (ValueError, OSError) as exc:
        raise WriteFailed(target, exc) from exc
    return Report(target=part, warnings=warnings)


def describe_source(source: str, options: ReadOptions) -> Info:
    frame, part, _ = read_frame(source, options)
    # to_json: missing values become null and dates ISO strings; without a path it returns the text
    preview = cast(str, frame.head(PREVIEW_ROWS).to_json(orient="records", force_ascii=False, date_format="iso"))
    return Info(
        source=part,
        types={str(column): str(dtype) for column, dtype in frame.dtypes.items()},
        preview=json.loads(preview),
    )
