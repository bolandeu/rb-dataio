"""The target columns: which columns of a table a write puts in the target, in what order and under what names.

`validate` refuses wrong names and clashes (INVALID_ARGUMENTS); `shaped` is the table with the target columns:
first the selection by `columns` (source names), then `rename` (old -> new). The write path calls both before
any backup, temporary file or remote call.
"""

from __future__ import annotations

import pandas as pd

from ..errors import InvalidParameter
from .options import WriteOptions
from .report import column_names


def _listed(names: list[str]) -> str:
    return ", ".join(names)


def _kept(frame: pd.DataFrame, options: WriteOptions) -> list[str]:
    """The source names the target keeps, in order; refuses a name the table does not have."""
    have = column_names(frame)
    if options.columns is None:
        return have
    for name in options.columns:
        if name not in have:
            raise InvalidParameter(
                f"columns names '{name}', which the table does not have. Columns there are: {_listed(have)}."
            )
    return list(options.columns)


def validate(frame: pd.DataFrame, options: WriteOptions) -> None:
    """Raise INVALID_ARGUMENTS for a name that is not a column, or a rename that makes two columns share a name."""
    kept = _kept(frame, options)
    rename = options.rename or {}
    for name in rename:
        if name not in kept:
            raise InvalidParameter(
                f"rename names '{name}', which is not among the target columns. Columns there are: {_listed(kept)}."
            )
    named = [rename.get(name, name) for name in kept]
    clashing = sorted({name for name in named if named.count(name) > 1})
    if clashing:
        raise InvalidParameter(f"The target would have the column name(s) {_listed(clashing)} more than once.")


def shaped(frame: pd.DataFrame, options: WriteOptions) -> pd.DataFrame:
    """The table with the target columns: selected by `columns`, then renamed by `rename`; `frame` itself with neither."""
    if options.columns is None and not options.rename:
        return frame
    validate(frame, options)
    named = frame.set_axis(column_names(frame), axis="columns")
    if options.columns is not None:
        named = named[list(options.columns)]
    return named.rename(columns=options.rename or {})
