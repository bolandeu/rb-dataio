"""jsonl: one JSON record per line; blank lines are skipped. Nested values as in json.py."""

from __future__ import annotations

import json

import pandas as pd

from ..core.dataio.options import ReadOptions, WriteOptions
from . import Loaded, TextAdapter
from .json import dumps, flat, records


class JsonlAdapter(TextAdapter):
    name = "jsonl"
    extensions = (".jsonl",)
    options = ("encoding",)

    def parse(self, text: str, options: ReadOptions) -> Loaded:
        rows = []
        for number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"line {number}: {exc.msg} (column {exc.colno}).") from exc
        return Loaded(flat(rows))

    def render(self, frame: pd.DataFrame, options: WriteOptions) -> str:
        return "".join(dumps(row) + "\n" for row in records(frame))


ADAPTER = JsonlAdapter()
