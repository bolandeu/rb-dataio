"""Value normalisation: the one step every read goes through after its adapter.

Header repair (empty and duplicate names, `col<N>` for a headerless table), empty rows
dropped, then the type of every text column: `dtypes` for the named columns, `as_text`
for all, else inferred. NA words never turn into missing values (the adapter reads them
as text); only an empty cell is missing. A column stays text when it could be an ID:
a value with a leading zero or `+`, or with more than 15 digits. `stack` joins tables of different
columns: a whole-number column stays whole (a nullable int) where a table lacks it. `typed` builds a table
from Python values and keeps a column of ints with a missing value whole in the same way.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

import pandas as pd

from ..errors import InvalidParameter
from .options import ReadOptions

_PATTERNS = {
    "int": r"[+-]?\d+",
    "float": r"[+-]?(\d+\.?\d*|\.\d+)",
    "date": r"\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?)?",
}
_CONVERTERS: dict[str, Callable[[pd.Series], pd.Series]] = {
    "int": lambda text: text.astype("Int64"),
    "float": lambda text: text.astype("float64"),
    "date": lambda text: pd.to_datetime(text, format="ISO8601", errors="coerce"),
}
_INFERRED = ("int", "float", "date")
_NUMBERS = ("int", "float")
DTYPES = (*_INFERRED, "str")
_ID_LIKE = re.compile(r"^(?:\+|[+-]?0\d)")
_MOST_DIGITS = 15


def normalise(frame: pd.DataFrame, options: ReadOptions, *, infer: bool = True) -> tuple[pd.DataFrame, list[str]]:
    """The normalised table and the warnings about what was repaired. `infer=False` keeps text columns text."""
    dtypes = options.dtypes or {}
    _require_known(frame, dtypes)
    frame, warnings = _repair_header(frame)
    frame = frame.dropna(how="all").reset_index(drop=True)
    for name in frame.columns:
        if name in dtypes:
            frame[name] = _cast(frame[name], dtypes[name])
        elif options.as_text:
            frame[name] = frame[name].astype("str")
        elif infer and pd.api.types.is_string_dtype(frame[name]):
            frame[name] = _infer(frame[name])
    return frame, warnings


def typed(frame: pd.DataFrame) -> pd.DataFrame:
    """The table of Python values (object columns) with its types set; ints with a missing value are Int64, not float."""
    columns = [_whole(frame.iloc[:, number]) for number in range(frame.shape[1])]
    typed_frame = pd.concat(columns, axis="columns") if columns else frame
    typed_frame.columns = frame.columns
    return typed_frame.infer_objects()


def _whole(column: pd.Series) -> pd.Series:
    present = column.dropna()
    if 0 < len(present) < len(column) and all(type(value) is int for value in present):
        return column.astype("Int64")
    return column


def stack(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """The tables one below the other; a column of whole numbers in every table that has it stays int, not float."""
    stacked = pd.concat(frames, ignore_index=True)
    if not stacked.columns.is_unique:
        return stacked
    for name in stacked.columns:
        owners = [frame[name] for frame in frames if name in frame.columns]
        if pd.api.types.is_float_dtype(stacked[name]) and all(pd.api.types.is_integer_dtype(c) for c in owners):
            stacked[name] = stacked[name].astype("Int64")
    return stacked


def _require_known(frame: pd.DataFrame, dtypes: dict[str, str]) -> None:
    for name, kind in dtypes.items():
        if kind not in DTYPES:
            raise InvalidParameter(f"dtypes of '{name}' must be one of {', '.join(DTYPES)}, not '{kind}'.")
        if name not in frame.columns and not isinstance(frame.columns, pd.RangeIndex):
            known = ", ".join(str(column) for column in frame.columns)
            raise InvalidParameter(
                f"dtypes names the column '{name}', which the table does not have. Columns: {known}."
            )


def _repair_header(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    if isinstance(frame.columns, pd.RangeIndex):  # no header row: the table asked for col1..colN
        return frame.set_axis([f"col{number}" for number in range(1, frame.shape[1] + 1)], axis="columns"), []
    names: list[str] = []
    repairs: list[str] = []
    for number, label in enumerate(frame.columns, start=1):
        wanted = "" if pd.isna(label) else str(label)
        name = _unique(wanted if wanted.strip() else f"col{number}", names)
        if name != wanted:
            repairs.append(f"column {number} '{wanted}' is now '{name}'")
        names.append(name)
    warning = [f"Repaired column names: {'; '.join(repairs)}."] if repairs else []
    return frame.set_axis(names, axis="columns"), warning


def _unique(name: str, taken: list[str]) -> str:
    candidate, number = name, 1
    while candidate in taken:
        number += 1
        candidate = f"{name}_{number}"
    return candidate


def _cast(column: pd.Series, kind: str) -> pd.Series:
    text = column.astype("str")
    if kind == "str":
        return text
    converted, unconverted = _convert(text, kind)
    if unconverted is not None:
        raise ValueError(f"column '{column.name}': cannot convert the value '{unconverted}' to {kind}.")
    return converted


def _infer(column: pd.Series) -> pd.Series:
    if column.notna().any():
        for kind in _INFERRED:
            if kind in _NUMBERS and _may_be_id(column):
                continue
            converted, unconverted = _convert(column, kind)
            if unconverted is None:
                return converted
    return column


def _may_be_id(column: pd.Series) -> bool:
    return bool(column.str.contains(_ID_LIKE).any() or (column.str.count(r"\d") > _MOST_DIGITS).any())


def _convert(column: pd.Series, kind: str) -> tuple[pd.Series, Any]:
    """The column as `kind` and the first value that is not one (None when all are); missing stays missing."""
    matches = column.str.fullmatch(_PATTERNS[kind], na=False)
    converted = _CONVERTERS[kind](column.where(matches))
    unconverted = column[column.notna() & converted.isna()]
    if kind == "int" and not converted.isna().any():
        converted = converted.astype("int64")
    return converted, (unconverted.iloc[0] if len(unconverted) else None)
