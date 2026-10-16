"""The CLI flags of the parameter vocabulary (core/dataio/options.py): one help text per word.

Typer names a flag after its Python parameter (`in_encoding` -> `--in-encoding`,
a boolean -> `--x/--no-x`), so a command parameter named like the library keyword
is the flag tests/test_parity.py expects. `side` is `in` or `out` in `convert`.
"""

from __future__ import annotations

from typing import Any

import typer

from ..core.errors import InvalidArguments

_HELP = {
    "format": "Format name; wins over the extension (see the formats command).",
    "sheet": "Sheet name; wins over the part of the address after #.",
    "table": "Table name; wins over the part of the address after #.",
    "encoding": "Text encoding, e.g. utf-8 or cp1251.",
    "sep": "Field delimiter, e.g. ';' or '|'.",
    "header": "The first row holds the column names.",
    "as_text": "Read every value as text.",
    "dtypes": "Type of one column as COLUMN=TYPE, e.g. freq=int; repeatable.",
    "limit": "Read at most this many rows.",
    "query": "SQL whose result is read: inside a base its tables, over any other source the table data.",
    "source_column": "Column that names the source of each row when an address names many sources.",
    "strict": "Sources with different columns fail with SCHEMA_MISMATCH instead of merging as a union.",
    "split_by": "Column whose values split the table into one target each, in a target with {column}.",
    "chunk_rows": "Rows per part, in a target with {n}.",
    "drop_split_column": "Leave the --split-by column out of the targets.",
    "keep_going": "Go on after a failed target; the report lists the failures in errors.",
    "mode": "Write mode: what to do with the data the target already has.",
    "profile": "Write profile, e.g. excel.",
    "credentials": "Key file (JSON) of the service, e.g. a Google service-account key; default: the standard order.",
    "start": "Top-left cell of the table in a sheet of a service, e.g. A5 (default A1).",
    "value_input": "How a sheet of a service takes the values: raw as they are, user as if typed.",
    "overwrite": "Allow a write over the source itself, or a replace of a sheet with rows that asks first.",
    "backup": "Keep a backup of the target before it is replaced.",
}
_SIDE = {None: "", "in": "Source: ", "out": "Target: "}


def option(word: str, default: Any, side: str | None = None, **extra: Any) -> Any:
    return typer.Option(default, help=_SIDE[side] + _HELP[word], **extra)


def pairs(values: list[str] | None) -> dict[str, str] | None:
    """`["freq=int"]` -> `{"freq": "int"}`, the shape of a dict flag."""
    if not values:
        return None
    if bad := [value for value in values if "=" not in value]:
        raise InvalidArguments(f"Expected COLUMN=TYPE, got: {', '.join(bad)}.")
    return dict(value.split("=", 1) for value in values)
