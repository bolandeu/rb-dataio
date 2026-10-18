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

from . import backup, batch, pipeline, registry
from .options import SOURCE_COLUMN, ReadOptions, WriteOptions
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
    credentials: str | None = None,
    as_text: bool = False,
    dtypes: dict[str, str] | None = None,
    limit: int | None = None,
    query: str | None = None,
    source_column: str | None = SOURCE_COLUMN,
    strict: bool = False,
) -> pd.DataFrame:
    """Read a source into a DataFrame: `read("phrases.csv")`, `read("book.xlsx#Sheet1")`, `read(["a", "b"])`.

    `format`, `sheet` and `table` win over what the address says; `limit` keeps the first rows.
    In a file of sheets or tables the first one is read when none is named; `#*` reads them all
    stacked, with the column `_sheet` naming the one of each row.
    A string with a line break is text; `format="text"` reads a one-line string as text too.
    `query` is SQL whose result is returned: inside a base it names the base's tables, over any
    other source the table is `data` (DuckDB reads a csv or parquet file itself).
    A Google Sheets URL names the sheet by its gid, `gsheet://<id>#Sheet1` by its name; `credentials`
    is a key file for such a source (else the google key is found in the standard order).
    An address that names many sources is read as one table: `source_column` names the column that says
    where each row came from (None leaves it out), `strict` makes different columns SCHEMA_MISMATCH.
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
    credentials: str | None = None,
    mode: str = "replace",
    start: str | None = None,
    value_input: str = "raw",
    profile: str | None = None,
    overwrite: bool = False,
    backup: bool = True,
    dry_run: bool = False,
    split_by: str | None = None,
    chunk_rows: int | None = None,
    drop_split_column: bool = False,
    keep_going: bool = False,
    columns: list[str] | None = None,
    rename: dict[str, str] | None = None,
) -> Any:
    """Write a DataFrame to a target and return the report (a `Report`): `write(df, "out.csv")`.

    `mode` is the write mode (`replace`, `append`, `error`); `dry_run` returns the report and writes nothing.
    With no target nothing is written: the data comes back as `format` says, `records` (the default),
    `list`, `dict`, or the text of `text`, `csv`, `json` and the other text formats.
    In a sheet of a service, `start` is the top-left cell (A1 when None) and `value_input` how it takes
    the values: `raw` as they are, `user` as if typed. A replace of a part with rows in a container that
    asks first (a Google sheet) needs `overwrite=True`; `credentials` is a key file for such a target.
    A target that is a template splits the table: `split_by` is the column, `chunk_rows` the rows of a part,
    `drop_split_column` leaves the column out; with `keep_going` a failed target does not stop the rest.
    `columns` are the source columns the target keeps, in this order; `rename` gives kept columns new names
    (old -> new): the selection comes first. A name the table lacks, or two columns with one name, is refused.
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
    in_credentials: str | None = None,
    as_text: bool = False,
    dtypes: dict[str, str] | None = None,
    limit: int | None = None,
    query: str | None = None,
    source_column: str | None = SOURCE_COLUMN,
    strict: bool = False,
    out_format: str | None = None,
    out_sheet: str | None = None,
    out_table: str | None = None,
    out_encoding: str | None = None,
    out_sep: str | None = None,
    out_header: bool = True,
    out_credentials: str | None = None,
    mode: str = "replace",
    start: str | None = None,
    value_input: str = "raw",
    profile: str | None = None,
    overwrite: bool = False,
    backup: bool = True,
    dry_run: bool = False,
    split_by: str | None = None,
    chunk_rows: int | None = None,
    drop_split_column: bool = False,
    keep_going: bool = False,
    columns: list[str] | None = None,
    rename: dict[str, str] | None = None,
) -> Report:
    """Read a source and write it to a target: `convert("a.csv", "b.csv")`; the report has both sides.

    The options both sides have take `in_` (the source) or `out_` (the target); `query` is of the source,
    `start`, `value_input`, `columns` and `rename` of the target. A target that is the source itself, or a part
    with rows in a container that asks first (a Google sheet), needs `overwrite=True`. Many sources merge and a template target
    splits (see `read` and `write`); many files to many targets, one to one, report `targets` and `errors`.
    """
    arguments = locals()
    write_options = WriteOptions.taken_from(arguments, "out")
    read_options = ReadOptions.taken_from(arguments, "in")
    if batch.converts_each(os.fspath(source), os.fspath(target)):
        return batch.convert_each(os.fspath(source), os.fspath(target), read_options, write_options)
    pipeline.refuse_over_source(os.fspath(source), os.fspath(target), write_options)
    frame, source_part, read_warnings = pipeline.read_frame(os.fspath(source), read_options)
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
    credentials: str | None = None,
    as_text: bool = False,
    dtypes: dict[str, str] | None = None,
    limit: int | None = None,
    query: str | None = None,
    source_column: str | None = SOURCE_COLUMN,
    strict: bool = False,
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
