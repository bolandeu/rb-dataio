"""CSV: UTF-8, `,` and a header row, unless `encoding=` or `sep=` name others."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..core.dataio.options import ReadOptions, SharedOptions, WriteOptions
from . import FormatAdapter, Loaded

ENCODING = "utf-8"
DELIMITER = ","


def _dialect(options: SharedOptions) -> tuple[str, str]:
    return options.encoding or ENCODING, options.sep or DELIMITER


class CsvAdapter(FormatAdapter):
    name = "csv"
    extensions = (".csv",)
    options = ("encoding", "sep")

    def read(self, path: Path, options: ReadOptions) -> Loaded:
        encoding, delimiter = _dialect(options)
        return Loaded(pd.read_csv(path, encoding=encoding, sep=delimiter), encoding, delimiter)

    def write(self, frame: pd.DataFrame, path: Path, options: WriteOptions) -> None:
        encoding, delimiter = _dialect(options)
        frame.to_csv(path, index=False, encoding=encoding, sep=delimiter)


ADAPTER = CsvAdapter()
