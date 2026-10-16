"""The sources seam of the read pipeline: an address that names many sources (a mask, a folder, a list).

`names_many` answers whether a source names many: a glob (`*`, `?`, `[`, `**`), a folder, or a list of
addresses (a list of plain lines stays the column `text`). `read_many` reads every file with the usual rules
and stacks the tables like `pipeline.read_frame`: the table, the source part of the report and the warnings.
Each row gets the column `options.source_column` (the file it came from; None leaves it out). Files with
different columns give their union and one warning; with `strict` that is SCHEMA_MISMATCH.
"""

from __future__ import annotations

import glob
import os
import re
from dataclasses import replace
from pathlib import Path

import pandas as pd

from ..errors import SchemaMismatch, SourceNotFound
from . import pipeline, values
from .address import FILE, parse
from .options import ReadOptions
from .report import SourcePart, column_names

_MAGIC = re.compile(r"[*?[]")


def names_many(source: object, options: ReadOptions) -> bool:
    if isinstance(source, list):
        return (
            bool(source)
            and all(isinstance(item, str | os.PathLike) for item in source)
            and any(_names_place(os.fspath(item), options) for item in source)
        )
    if isinstance(source, str | os.PathLike):
        text = os.fspath(source)
        return not _is_text(text, options) and _is_pattern_or_folder(parse(text).path, parse(text).scheme)
    return False


def _is_text(text: str, options: ReadOptions) -> bool:
    return "\n" in text or options.format == "text"


def _is_pattern_or_folder(path: str, scheme: str) -> bool:
    if scheme != FILE:
        return False
    return os.path.isdir(path) or (bool(_MAGIC.search(path)) and not os.path.exists(path))


def _names_place(text: str, options: ReadOptions) -> bool:
    """A list item that is an address of a file, a folder or a mask, not a line of text."""
    if _is_text(text, options):
        return False
    address = parse(text)
    return address.scheme == FILE and (os.path.exists(address.path) or bool(_MAGIC.search(address.path)))


def read_many(source: object, options: ReadOptions) -> tuple[pd.DataFrame, SourcePart, list[str]]:
    items = _addresses(source)
    each = replace(options, limit=None)
    reads = [(place, *pipeline.read_frame(place, each)) for item in items for place in _expand(item)]
    reads = [(parse(place).path, frame, part, found) for place, frame, part, found in reads]
    columns_by_source = {name: column_names(frame) for name, frame, _, _ in reads}
    differing = _differing(list(columns_by_source.values()))
    if differing and options.strict:
        raise SchemaMismatch(columns_by_source)
    frames = [frame for _, frame, _, _ in reads]
    if options.source_column is not None:
        frames = [_named(frame, options.source_column, name) for name, frame, _, _ in reads]
    merged = values.stack(frames)
    if options.limit is not None:
        merged = merged.head(options.limit)
    warnings = [f"{name}: {warning}" for name, _, _, found in reads for warning in found]
    if differing:
        warnings.append(
            f"the sources have different columns: {', '.join(differing)}; a source without one leaves it empty"
        )
    parts = [part for _, _, part, _ in reads]
    return merged, _merged_part(items, parts, merged), warnings


def _addresses(source: object) -> list[str]:
    given = source if isinstance(source, list) else [source]
    return [os.fspath(item) for item in given if isinstance(item, str | os.PathLike)]


def _named(frame: pd.DataFrame, column: str, name: str) -> pd.DataFrame:
    named = frame.copy()
    named.insert(0, column, name)
    return named


def _differing(column_lists: list[list[str]]) -> list[str]:
    """The columns that not every source has, in the order they first appear."""
    every = [set(columns) for columns in column_lists]
    first_seen = dict.fromkeys(column for columns in column_lists for column in columns)
    return [column for column in first_seen if not all(column in columns for columns in every)]


def _merged_part(items: list[str], parts: list[SourcePart], merged: pd.DataFrame) -> SourcePart:
    """The source part of a merge: the addresses as written, the formats of the files, the shared encoding and delimiter."""
    encodings = {part.encoding for part in parts}
    delimiters = {part.delimiter for part in parts}
    return SourcePart(
        uri=", ".join(items),
        format=", ".join(dict.fromkeys(part.format for part in parts)),
        encoding=encodings.pop() if len(encodings) == 1 else None,
        delimiter=delimiters.pop() if len(delimiters) == 1 else None,
        rows=len(merged),
        columns=column_names(merged),
    )


def _expand(item: str) -> list[str]:
    """The addresses of the files an item names: itself, the files of a mask or of a folder (the fragment kept)."""
    address = parse(item)
    if address.scheme != FILE or not (_MAGIC.search(address.path) or os.path.isdir(address.path)):
        return [item]
    suffix = f"#{address.fragment}" if address.fragment is not None else ""
    if os.path.isdir(address.path):
        paths = [str(path) for path in Path(address.path).iterdir() if path.is_file() and not path.name.startswith(".")]
    else:
        paths = [path for path in glob.glob(address.path, recursive=True) if os.path.isfile(path)]
    if not paths:
        raise SourceNotFound(item)
    return [f"{path}{suffix}" for path in sorted(paths)]
