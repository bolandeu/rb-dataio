"""Parquet: read and written through DuckDB (ADR 0003), never pyarrow; it does not append.

A read keeps the types the file stores: a string column holding '007' stays text, so the
leading-zero rule has nothing to re-type. A write stores each column with the type of its
dtype, missing values as nulls.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from ..core.dataio.options import ReadOptions, WriteOptions
from . import FormatAdapter, Loaded


def _quoted(path: Path) -> str:
    return "'" + str(path).replace("'", "''") + "'"


class ParquetAdapter(FormatAdapter):
    name = "parquet"
    extensions = (".parquet",)
    options = ()

    def read(self, path: Path, options: ReadOptions) -> Loaded:
        with duckdb.connect() as connection:
            frame = connection.execute("SELECT * FROM read_parquet(?)", [str(path)]).df()
        return Loaded(frame, infers_types=False)

    def write(self, frame: pd.DataFrame, path: Path, options: WriteOptions) -> None:
        with duckdb.connect() as connection:
            connection.register("frame", frame)
            connection.execute(f"COPY frame TO {_quoted(path)} (FORMAT PARQUET)")


ADAPTER = ParquetAdapter()
