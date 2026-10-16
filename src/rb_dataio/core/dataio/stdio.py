"""The address `-`: stdin as a source, stdout as a target.

stdin has no extension: its format is `format=` or comes from the content: JSON when it
starts with `[` (or `{` and is one JSON document), jsonl when it starts with `{`, CSV when
its lines agree on a delimiter, else txt. stdout gets CSV, or one value per line for one
column; an object format (`records`, `list`, `dict`) is no text: the report carries it as `data`.
"""

from __future__ import annotations

import json
import sys
from typing import Any

import pandas as pd

from ...formats import ENCODING, Loaded, decode
from ...formats import csv as csv_format
from ...formats import json as json_format
from ...formats import jsonl as jsonl_format
from ...formats import txt as txt_format
from . import objects, registry
from .address import STDIO_TEXT
from .options import ReadOptions, WriteOptions


def read(options: ReadOptions) -> tuple[str, Loaded]:
    """The format name and the table of stdin."""
    data = sys.stdin.buffer.read()
    adapter = registry.text_adapter(options.format or detect(decode(data, options.encoding)[0]), STDIO_TEXT)
    return adapter.name, adapter.load(data, options)


def detect(text: str) -> str:
    """The format of a text with no name, from its content."""
    start = text.lstrip()[:1]
    if start == "[" or (start == "{" and _is_one_document(text)):
        return json_format.ADAPTER.name
    if start == "{":
        return jsonl_format.ADAPTER.name
    return csv_format.ADAPTER.name if csv_format.sniff_delimiter(text) else txt_format.ADAPTER.name


def _is_one_document(text: str) -> bool:
    try:
        json.loads(text)
    except json.JSONDecodeError:
        return False
    return True


def format_of(frame: pd.DataFrame, options: WriteOptions) -> str:
    """The format stdout gets: `format=`, else txt for one column and CSV for more."""
    if options.format:
        return options.format
    return (txt_format.ADAPTER if frame.shape[1] == 1 else csv_format.ADAPTER).name


def write(frame: pd.DataFrame, format_name: str, options: WriteOptions) -> Any:
    """Write `frame` to stdout as `format_name`; an object format writes nothing and returns its object."""
    data = objects.rendered(frame, format_name, options, STDIO_TEXT)
    if format_name in objects.OBJECT_FORMATS:
        return data
    sys.stdout.flush()  # what was written as text before goes first
    sys.stdout.buffer.write(data.encode(options.encoding or ENCODING))
    sys.stdout.buffer.flush()
    return None
