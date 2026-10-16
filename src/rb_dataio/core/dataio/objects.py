"""Python objects: the in-memory sources of `read()` and the in-memory results of `write()`.

In: a list of strings, or a string with a line break, is the one column `text`; a list of
dicts is records; a dict of lists is columns, any other dict the columns `key` and `value`;
a Series is its column (`value` when unnamed); a DataFrame is itself. Records flatten as
in JSON. A one-line string is an address (docs/adr/0004), unless `format="text"`.
Out: `records`, `list` (the first column) and `dict` (columns of values) are objects;
`text` and the text formats (`csv`, `json`, ...) are the text their file would hold.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from ...formats import Loaded
from ...formats.json import flat, plain, records
from ...formats.txt import lines_table
from ..errors import InvalidParameter
from . import registry
from .options import ReadOptions, WriteOptions

RECORDS = "records"
OBJECT_FORMATS: dict[str, Callable[[pd.DataFrame], Any]] = {
    RECORDS: records,
    "list": lambda frame: plain(frame).iloc[:, 0].tolist(),
    "dict": lambda frame: plain(frame).to_dict("list"),
}
_KEY, _VALUE = "key", "value"


def is_text(source: str, options: ReadOptions) -> bool:
    """A string with a line break, or any string under `format="text"`, is data, not an address."""
    return "\n" in source or options.format == registry.TEXT


def loaded(data: object) -> Loaded:
    """The table of a Python object."""
    if isinstance(data, pd.DataFrame):
        return Loaded(data.copy())
    if isinstance(data, pd.Series):
        return Loaded(data.to_frame(_VALUE if data.name is None else data.name))
    if isinstance(data, dict):
        return Loaded(_columns(data))
    if isinstance(data, list) and all(isinstance(item, str) for item in data):
        return Loaded(lines_table(data).frame, infers_types=False)
    if isinstance(data, list) and all(isinstance(item, dict) for item in data):
        return Loaded(flat(data))
    raise InvalidParameter(
        f"Cannot read a {type(data).__name__} as a table: pass a DataFrame, a Series, a dict, "
        "a list of strings or of dicts, a text with line breaks, or an address."
    )


def _columns(data: dict[Any, Any]) -> pd.DataFrame:
    if data and all(isinstance(value, list | tuple) for value in data.values()):
        return pd.DataFrame(data)
    return pd.DataFrame({_KEY: list(data), _VALUE: list(data.values())})


def rendered(frame: pd.DataFrame, format_name: str, options: WriteOptions, uri: str) -> Any:
    """`frame` as `format_name`: the object of an object format, else the text of a text format."""
    if to_object := OBJECT_FORMATS.get(format_name):
        return to_object(frame)
    return registry.text_adapter(format_name, uri, also=tuple(OBJECT_FORMATS)).render(frame, options)
