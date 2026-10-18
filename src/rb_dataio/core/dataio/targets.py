"""The targets seam of the write pipeline: a target address that is a template (`out/{region}.csv`, `out/part_{n}.csv`).

`is_template` answers whether a target has a placeholder to fill (`{stem}` is the batch convert's, not this one's);
`require_placeholder` refuses `split_by` or `chunk_rows` with a target that has none.
`write_many` splits the frame by the column `split_by` (`{region}`) or by `chunk_rows` rows (`{n}`, from 1) and writes
each part to its own target through `pipeline.write_frame`, so each has its mode, backup and checks. A placeholder in
the path makes a file name, one after the `#` a sheet name; a value is made safe for it first. The report lists the
final names in `targets` (and, with `keep_going`, the failed ones in `errors`).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pandas as pd

from ..errors import DataioError, InvalidParameter
from . import columns as columns_module
from .address import FILE, parse
from .options import WriteOptions
from .report import BatchError, BatchTarget, PlannedBatchTarget, PlannedTarget, Report

_PLACEHOLDER = re.compile(r"\{(\w+)\}")
_NOT_IN_FILE_NAME = re.compile(r'[\\/:*?"<>|{}\x00-\x1f]')
_NOT_IN_SHEET_NAME = re.compile(r"[\[\]:*?/\\{}\x00-\x1f]")
SHEET_NAME_LIMIT = 31  # the longest sheet name of an xlsx book
CHUNK_PLACEHOLDER = "n"
BATCH_PLACEHOLDER = "stem"  # the placeholder of `convert` of many files (batch.py)


def _placeholders(target: str) -> list[str]:
    return [name for name in _PLACEHOLDER.findall(target) if name != BATCH_PLACEHOLDER]


def is_template(target: str, options: WriteOptions) -> bool:
    return bool(_placeholders(target))


def require_placeholder(target: str, options: WriteOptions) -> None:
    """INVALID_ARGUMENTS when the write asks for a split and the target has no placeholder to name the parts."""
    if (options.split_by is not None or options.chunk_rows is not None) and not _placeholders(target):
        raise InvalidParameter(
            f"Target '{target}' has no placeholder: with split_by it needs {{column}}, with chunk_rows {{n}}."
        )


def _safe_file_name(value: object) -> str:
    return _NOT_IN_FILE_NAME.sub("_", str(value)).strip(" .") or "_"


def _safe_sheet_name(value: object) -> str:
    return _NOT_IN_SHEET_NAME.sub("_", str(value))[:SHEET_NAME_LIMIT].strip("'") or "_"


def _filled(target: str, name: str, value: object) -> str:
    """`target` with `{name}` replaced by `value`, safe for a file name before the `#` and for a sheet name after it."""
    path, hash_sign, sheet = target.partition("#")
    fill = _PLACEHOLDER.sub
    path = fill(lambda found: _safe_file_name(value) if found[1] == name else found[0], path)
    sheet = fill(lambda found: _safe_sheet_name(value) if found[1] == name else found[0], sheet)
    return path + hash_sign + sheet


def _check(frame: pd.DataFrame, target: str, options: WriteOptions) -> str:
    """The name of the placeholder this write fills; INVALID_ARGUMENTS when the target and the options disagree."""
    if (options.split_by is None) == (options.chunk_rows is None):
        raise InvalidParameter(f"Target '{target}' is a template: pass split_by or chunk_rows, one of them.")
    name = options.split_by if options.split_by is not None else CHUNK_PLACEHOLDER
    if options.split_by is not None and options.split_by not in frame.columns:
        raise InvalidParameter(f"split_by column '{options.split_by}' is not in the table: {list(frame.columns)}.")
    if set(_placeholders(target)) != {name}:
        raise InvalidParameter(f"Target '{target}' must hold only the placeholder {{{name}}}.")
    if "#" in target and _PLACEHOLDER.search(target.partition("#")[2]) and (options.sheet or options.table):
        raise InvalidParameter(f"Target '{target}' names its sheets by a template: do not pass sheet or table.")
    return name


def _parts(frame: pd.DataFrame, target: str, options: WriteOptions) -> Iterator[tuple[str, pd.DataFrame]]:
    """Each target address with its rows, in the order the values (or the chunks) come."""
    name = _check(frame, target, options)
    if options.split_by is not None:
        column = options.split_by
        for value, part in frame.groupby(column, sort=False, dropna=False):
            yield _filled(target, name, value), part.drop(columns=[column]) if options.drop_split_column else part
        return
    size = options.chunk_rows or 1
    for number, start in enumerate(range(0, max(len(frame), 1), size), start=1):
        yield _filled(target, name, number), frame.iloc[start : start + size]


def _batch_target(uri: str, rows: int, planned: object) -> BatchTarget:
    if isinstance(planned, PlannedTarget):
        return PlannedBatchTarget(
            uri=uri, rows=rows, exists=planned.exists, rows_before=planned.rows_before, rows_after=planned.rows_after
        )
    return BatchTarget(uri=uri, rows=rows)


def _make_folder(uri: str, options: WriteOptions) -> None:
    """The folder of a file target, made: a split writes many files into a folder the caller names once."""
    address = parse(uri)
    if address.scheme == FILE and not options.dry_run:
        Path(address.path).parent.mkdir(parents=True, exist_ok=True)


def _part_options(frame: pd.DataFrame, options: WriteOptions) -> WriteOptions:
    """The options of one part: the target columns checked once on the whole table, a dropped split column left out."""
    whole = frame
    columns = options.columns
    if options.split_by is not None and options.drop_split_column:
        whole = frame.drop(columns=[options.split_by])
        columns = None if columns is None else [name for name in columns if name != options.split_by]
    each = replace(
        options, columns=columns, split_by=None, chunk_rows=None
    )  # a part's target is a name, not a template
    columns_module.validate(whole, each)
    return each


def write_many(frame: pd.DataFrame, target: str, options: WriteOptions) -> Report:
    from . import pipeline  # pipeline imports this module

    parts = list(_parts(frame, target, options))
    each = _part_options(frame, options)
    uris = [uri.casefold() for uri, _ in parts]
    if len(set(uris)) < len(uris):
        raise InvalidParameter(f"Two values of the table get the same name in '{target}' once made safe.")
    written: list[BatchTarget] = []
    errors: list[BatchError] = []
    warnings: list[str] = []
    for uri, part in parts:
        try:
            _make_folder(uri, options)
            report = pipeline.write_frame(part, uri, each)
        except DataioError as exc:
            if not options.keep_going:
                raise
            errors.append(BatchError(uri=uri, code=exc.code, message=exc.message))
            continue
        written.append(_batch_target(uri, len(part), report.target))
        warnings.extend(report.warnings)
    return Report(targets=written, errors=errors or None, warnings=warnings)
