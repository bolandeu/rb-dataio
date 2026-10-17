"""JSON: an array of records or an object of columns; a write is records with indent 2.

A read flattens nested objects into `a.b` columns and keeps a nested list as its JSON text;
an object whose values are not all lists is one record. A write keeps real Cyrillic (no
`\\u` escapes) and writes dates as ISO 8601. `plain`, `records` and `flat` also serve jsonl.py and
the Python objects of `read()` and `write()`.
"""

from __future__ import annotations

import datetime as dt
import json
from typing import Any

import pandas as pd

from ..core.dataio.options import ReadOptions, WriteOptions
from ..core.dataio.values import typed
from . import Loaded, TextAdapter

INDENT = 2


def plain(frame: pd.DataFrame) -> pd.DataFrame:
    """The table with plain Python values; a missing value is None."""
    return frame.astype(object).where(frame.notna(), None)


def records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return plain(frame).to_dict("records")


def flat(rows: list[Any]) -> pd.DataFrame:
    """Records as a table: a nested object becomes `a.b` columns, a nested list its JSON text."""
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("expected records: every item must be an object.")
    return typed(pd.DataFrame([_cells(row) for row in rows], dtype=object))


def _cells(record: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """One record as flat cells: a nested object becomes `a.b` keys, a nested list its JSON text."""
    cells: dict[str, Any] = {}
    for name, value in record.items():
        if isinstance(value, dict):
            cells.update(_cells(value, f"{prefix}{name}."))
        else:
            cells[f"{prefix}{name}"] = dumps(value) if isinstance(value, list) else value
    return cells


def dumps(value: Any, indent: int | None = None) -> str:
    return json.dumps(value, ensure_ascii=False, indent=indent, default=_iso)


def _iso(value: Any) -> str:
    if isinstance(value, dt.date):  # a pandas Timestamp is a datetime, a datetime is a date
        return value.isoformat()
    raise TypeError(f"{type(value).__name__} is not JSON: {value!r}")


def _is_columns(data: dict[str, Any]) -> bool:
    return bool(data) and all(isinstance(value, list) for value in data.values())


class JsonAdapter(TextAdapter):
    name = "json"
    extensions = (".json",)
    options = ("encoding",)

    def parse(self, text: str, options: ReadOptions) -> Loaded:
        data = json.loads(text)  # a JSONDecodeError names the line and the column
        if isinstance(data, dict):
            return Loaded(pd.DataFrame(data) if _is_columns(data) else flat([data]))
        if isinstance(data, list):
            return Loaded(flat(data))
        raise ValueError(f"expected an array of records or an object, not {type(data).__name__}.")

    def render(self, frame: pd.DataFrame, options: WriteOptions) -> str:
        return dumps(records(frame), indent=INDENT) + "\n"


ADAPTER = JsonAdapter()
