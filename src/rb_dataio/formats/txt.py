"""Text: one line is one value of the single column `text`; blank lines are skipped by value normalisation."""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from ..core.dataio.options import Mode, ReadOptions, WriteOptions
from ..core.dataio.report import column_names
from . import FormatAdapter, Loaded
from .csv import ENCODING, append_text, decode, existing_text

COLUMN = "text"


class TxtAdapter(FormatAdapter):
    name = "txt"
    extensions = (".txt",)
    options = ("encoding",)
    appends = True
    infers_types = False  # a phrase list stays text, whatever the lines look like

    def read(self, path: Path, options: ReadOptions) -> Loaded:
        text, encoding = decode(path.read_bytes(), options.encoding)
        lines = [line.rstrip("\n") for line in io.StringIO(text)]
        values = pd.Series([line if line.strip() else None for line in lines], name=COLUMN, dtype="str")
        return Loaded(values.to_frame(), encoding)

    def write(self, frame: pd.DataFrame, path: Path, options: WriteOptions) -> None:
        if frame.shape[1] != 1:
            raise ValueError(f"txt holds one column, the data has {frame.shape[1]}: {column_names(frame)}.")
        text = "".join(f"{value}\n" for value in frame.iloc[:, 0].fillna(""))
        existing = existing_text(path, options) if options.mode is Mode.APPEND else None
        if existing is None:
            path.write_bytes(text.encode(options.encoding or ENCODING))
        else:
            append_text(path, existing, text)


ADAPTER = TxtAdapter()
