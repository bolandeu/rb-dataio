"""`query=`: SQL whose result is the table a read returns.

    a base               the SQL runs inside the base, on its own tables (formats.BaseAdapter)
    a csv or parquet     DuckDB reads the file itself as the table `data` (the adapter's `query`)
    any other source     the table read as usual is `data` in an in-memory DuckDB (`over_table`)

So a large csv or parquet file never reaches pandas whole, only the result does. The
table `data` has the types of a read without `as_text` and `dtypes` (DuckDB's own over a
file it reads itself); `as_text`, `dtypes` and `limit` apply to the result. An error of
the SQL is a ValueError with the message of DuckDB: the read pipeline reports it as READ_FAILED.
"""

from __future__ import annotations

from dataclasses import replace

import duckdb
import pandas as pd

from ...formats import Loaded
from . import values
from .options import ReadOptions

TABLE = "data"


def literal(text: str) -> str:
    """`text` as a SQL string literal, for a path in a table function."""
    return "'" + text.replace("'", "''") + "'"


def over_file(function: str, sql: str) -> pd.DataFrame:
    """The result of `sql` where `data` is the DuckDB table function `function`, e.g. `read_parquet('a.parquet')`."""
    with duckdb.connect() as connection:
        connection.execute(f"CREATE VIEW {TABLE} AS SELECT * FROM {function}")  # noqa: S608 -- paths in it are literal()
        return _result(connection, sql)


def over_table(loaded: Loaded, options: ReadOptions) -> Loaded:
    """`loaded` itself with no `query=`; else the result of the query, the table normalised being `data`."""
    if not options.query:
        return loaded
    frame, warnings = values.normalise(
        loaded.frame, replace(options, as_text=False, dtypes=None), infer=loaded.infers_types
    )
    with duckdb.connect() as connection:
        connection.register(TABLE, frame)
        result = _result(connection, options.query)
    return replace(loaded, frame=result, infers_types=False, warnings=(*loaded.warnings, *warnings))


def _result(connection: duckdb.DuckDBPyConnection, sql: str) -> pd.DataFrame:
    try:
        return connection.execute(sql).df()
    except duckdb.Error as exc:
        raise ValueError(str(exc)) from exc
