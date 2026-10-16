"""Text: one line is one value of the single column `text`; blank lines are skipped by value normalisation."""

from __future__ import annotations

import io
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from ..core.dataio.options import Mode, ReadOptions, WriteOptions
from ..core.dataio.report import column_names
from . import Loaded, TextAdapter
from .csv import append_text, existing_text

COLUMN = "text"


def lines_table(lines: Iterable[str]) -> Loaded:
    """The column `text` of the lines; a blank line is an empty row, and the values stay text."""
    values = pd.Series([line if line.strip() else None for line in lines], name=COLUMN, dtype="str")
    return Loaded(values.to_frame(), infers_types=False)


class TxtAdapter(TextAdapter):
    name = "txt"
    extensions = (".txt",)
    options = ("encoding",)
    appends = True

    def parse(self, text: str, options: ReadOptions) -> Loaded:
        return lines_table(line.rstrip("\n") for line in io.StringIO(text))

    def render(self, frame: pd.DataFrame, options: WriteOptions) -> str:
        if frame.shape[1] != 1:
            raise ValueError(f"txt holds one column, the data has {frame.shape[1]}: {column_names(frame)}.")
        return "".join(f"{value}\n" for value in frame.iloc[:, 0].fillna(""))

    def write(self, frame: pd.DataFrame, path: Path, options: WriteOptions) -> None:
        existing = existing_text(path, options) if options.mode is Mode.APPEND else None
        if existing is None:
            super().write(frame, path, options)
        else:
            append_text(path, existing, self.render(frame, options))


ADAPTER = TxtAdapter()
