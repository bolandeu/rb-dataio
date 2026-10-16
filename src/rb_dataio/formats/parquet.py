"""Parquet: read and written through DuckDB (ADR 0003), never pyarrow; it does not append.

A read keeps the types the file stores: a string column holding '007' stays text, so the
leading-zero rule has nothing to re-type. A write stores each column with the type of its
dtype, missing values as nulls. `query=` is run by DuckDB on the file itself.
`read_file` and `write_file` serve the backup store too, which keeps the old rows of a table as parquet.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from ..core.dataio import query
from ..core.dataio.options import ReadOptions, WriteOptions
from . import FormatAdapter, Loaded


def read_file(path: Path) -> pd.DataFrame:
    with duckdb.connect() as connection:
        return connection.execute("SELECT * FROM read_parquet(?)", [str(path)]).df()


def write_file(frame: pd.DataFrame, path: Path) -> None:
    with duckdb.connect() as connection:
        connection.register("frame", frame)
        connection.execute(f"COPY frame TO {query.literal(str(path))} (FORMAT PARQUET)")


class ParquetAdapter(FormatAdapter):
    name = "parquet"
    extensions = (".parquet",)
    options = ()

    def read(self, path: Path, options: ReadOptions) -> Loaded:
        return Loaded(read_file(path), infers_types=False)

    def write(self, frame: pd.DataFrame, path: Path, options: WriteOptions) -> None:
        write_file(frame, path)

    def query(self, path: Path, sql: str, options: ReadOptions) -> Loaded:
        return Loaded(query.over_file(f"read_parquet({query.literal(str(path))})", sql), infers_types=False)


ADAPTER = ParquetAdapter()
