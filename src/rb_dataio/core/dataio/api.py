"""The public library API, re-exported by the package root.

Every keyword here is a CLI flag with the same name (docs/adr/0001, tests/test_parity.py):
`read()` and `write()` reach the CLI through `convert`, where the options both sides
have take `in_` / `out_`. A parameter whose behaviour comes with a later task is
accepted and passed on already, so later tasks change behaviour, not the surface.
"""

from __future__ import annotations

import os
from typing import Any

import pandas as pd

from . import backup, pipeline, registry
from .options import ReadOptions, WriteOptions
from .report import Backup, FormatInfo, Info, Report

# An address, a text with line breaks, or a Python object that is a table (core/dataio/objects.py).
Source = str | os.PathLike[str] | pd.DataFrame | pd.Series | list[str] | list[dict[str, Any]] | dict[Any, Any]


def read(
    source: Source,
    *,
    format: str | None = None,
    sheet: str | None = None,
    table: str | None = None,
    encoding: str | None = None,
    sep: str | None = None,
    header: bool = True,
    as_text: bool = False,
    dtypes: dict[str, str] | None = None,
    limit: int | None = None,
    query: str | None = None,
) -> pd.DataFrame:
    """Read a source into a DataFrame: `read("phrases.csv")`, `read("book.xlsx#Sheet1")`, `read(["a", "b"])`.

    `format`, `sheet` and `table` win over what the address says; `limit` keeps the first rows.
    In a file of sheets or tables the first one is read when none is named; `#*` reads them all
    stacked, with the column `_sheet` naming the one of each row.
    A string with a line break is text; `format="text"` reads a one-line string as text too.
    `query` is SQL whose result is returned: inside a base it names the base's tables, over any
    other source the table is `data` (DuckDB reads a csv or parquet file itself).
    """
    frame, _, _ = pipeline.read_frame(source, ReadOptions.taken_from(locals()))
    return frame


def write(
    df: pd.DataFrame,
    target: str | os.PathLike[str] | None = None,
    *,
    format: str | None = None,
    sheet: str | None = None,
    table: str | None = None,
    encoding: str | None = None,
    sep: str | None = None,
    header: bool = True,
    mode: str = "replace",
    profile: str | None = None,
    overwrite: bool = False,
    backup: bool = True,
    dry_run: bool = False,
) -> Any:
    """Write a DataFrame to a target and return the report (a `Report`): `write(df, "out.csv")`.

    `mode` is the write mode (`replace`, `append`, `error`); `dry_run` returns the report and writes nothing.
    With no target nothing is written: the data comes back as `format` says, `records` (the default),
    `list`, `dict`, or the text of `text`, `csv`, `json` and the other text formats.
    """
    options = WriteOptions.taken_from(locals())
    if target is None:
        return pipeline.frame_data(df, options)
    return pipeline.write_frame(df, os.fspath(target), options)


def convert(
    source: str | os.PathLike[str],
    target: str | os.PathLike[str],
    *,
    in_format: str | None = None,
    in_sheet: str | None = None,
    in_table: str | None = None,
    in_encoding: str | None = None,
    in_sep: str | None = None,
    in_header: bool = True,
    as_text: bool = False,
    dtypes: dict[str, str] | None = None,
    limit: int | None = None,
    query: str | None = None,
    out_format: str | None = None,
    out_sheet: str | None = None,
    out_table: str | None = None,
    out_encoding: str | None = None,
    out_sep: str | None = None,
    out_header: bool = True,
    mode: str = "replace",
    profile: str | None = None,
    overwrite: bool = False,
    backup: bool = True,
    dry_run: bool = False,
) -> Report:
    """Read a source and write it to a target: `convert("a.csv", "b.csv")`; the report has both sides.

    The options both sides have take `in_` (the source) or `out_` (the target); `query` is of the source.
    A target that is the source itself needs `overwrite=True`.
    """
    arguments = locals()
    write_options = WriteOptions.taken_from(arguments, "out")
    pipeline.refuse_over_source(os.fspath(source), os.fspath(target), write_options)
    frame, source_part, read_warnings = pipeline.read_frame(os.fspath(source), ReadOptions.taken_from(arguments, "in"))
    report = pipeline.write_frame(frame, os.fspath(target), write_options)
    return report.model_copy(update={"source": source_part, "warnings": [*read_warnings, *report.warnings]})


def info(
    source: str | os.PathLike[str],
    *,
    format: str | None = None,
    sheet: str | None = None,
    table: str | None = None,
    encoding: str | None = None,
    sep: str | None = None,
    header: bool = True,
    as_text: bool = False,
    dtypes: dict[str, str] | None = None,
    limit: int | None = None,
    query: str | None = None,
) -> Info:
    """Describe a source before a convert: its format, rows, column types, the first 5 rows and its sheets or tables.

    With `query` it describes the result of the query, as `read()` returns it.
    """
    return pipeline.describe_source(os.fspath(source), ReadOptions.taken_from(locals()))


def formats() -> list[FormatInfo]:
    """Every format this release knows: what it can read, write and append, and the options it honours."""
    return registry.describe()


def backups() -> list[Backup]:
    """The kept backups, newest first: every replace of an existing target keeps one."""
    return backup.entries()


def restore(id: str | None = None, *, dry_run: bool = False) -> Report:
    """Bring back the backup `id` (the newest without one) into its target.

    What the target holds now is kept as a new backup first, so a restore can be undone.
    `dry_run` returns the report and changes nothing.
    """
    return pipeline.restore_target(id, dry_run)
