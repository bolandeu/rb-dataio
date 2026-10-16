"""DuckDB bases: `x.duckdb#table` and `.db` files with the DuckDB signature, read and written through the duckdb package.

A base is a container of tables (`BaseAdapter`): the table comes from the address or `table=`; with no name, one
table is read, and several are listed in SOURCE_NOT_FOUND. `query=` runs inside the base. A write is one
transaction on the base itself: replace drops and creates the table (the core keeps the old rows as a backup),
append adds rows and never changes the schema (a column the table lacks is refused by name, a column the frame
lacks is NULL). A write that fails midway leaves the base as it was; a base another connection holds is refused
with the action to close that connection. Columns are stored as BIGINT, DOUBLE, VARCHAR, TIMESTAMP and BOOLEAN.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import closing, contextmanager
from pathlib import Path

import duckdb
import pandas as pd
from pandas.api import types

from ..core.dataio.options import Mode, ReadOptions, WriteOptions
from . import AppendRefused, BaseAdapter, Loaded, WriteRefused

SIGNATURE = b"DUCK"  # the four bytes after the 8-byte checksum of the file header
SIGNATURE_OFFSET = 8
LOCKED_ACTION = "Close the other connection to the base, then write again."
INCOMING = "incoming"  # the name the frame gets inside the transaction


def _identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _column_type(dtype: object) -> str:
    if types.is_bool_dtype(dtype):
        return "BOOLEAN"
    if types.is_integer_dtype(dtype):
        return "BIGINT"
    if types.is_float_dtype(dtype):
        return "DOUBLE"
    if types.is_datetime64_any_dtype(dtype):
        return "TIMESTAMP"
    return "VARCHAR"


@contextmanager
def _connection(path: Path, *, read_only: bool) -> Generator[duckdb.DuckDBPyConnection]:
    """The base opened and closed; an error of DuckDB is a ValueError, a base held elsewhere refuses a write."""
    try:
        with closing(duckdb.connect(str(path), read_only=read_only)) as connection:
            yield connection
    except (duckdb.IOException, duckdb.ConnectionException) as exc:
        if read_only:
            raise ValueError(str(exc)) from exc
        raise WriteRefused(str(exc), action=LOCKED_ACTION) from exc
    except duckdb.Error as exc:
        raise ValueError(str(exc)) from exc


@contextmanager
def _transaction(path: Path) -> Generator[duckdb.DuckDBPyConnection]:
    with _connection(path, read_only=False) as connection:
        connection.begin()
        try:
            yield connection
        except BaseException:
            connection.rollback()
            raise
        connection.commit()


def _tables(connection: duckdb.DuckDBPyConnection) -> list[str]:
    rows = connection.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main' AND table_type = 'BASE TABLE'"
        " ORDER BY table_name"
    ).fetchall()
    return [name for (name,) in rows]


def _columns(connection: duckdb.DuckDBPyConnection, table: str) -> list[str]:
    return [name for (name, *_) in connection.execute(f"DESCRIBE {_identifier(table)}").fetchall()]


def _count(connection: duckdb.DuckDBPyConnection, table: str) -> int:
    counted = connection.execute(f"SELECT count(*) FROM {_identifier(table)}").fetchall()  # noqa: S608 -- quoted
    return counted[0][0]


def _create(connection: duckdb.DuckDBPyConnection, table: str, frame: pd.DataFrame) -> None:
    columns = ", ".join(f"{_identifier(str(name))} {_column_type(dtype)}" for name, dtype in frame.dtypes.items())
    connection.execute(f"CREATE TABLE {_identifier(table)} ({columns})")


def _insert(connection: duckdb.DuckDBPyConnection, table: str, frame: pd.DataFrame) -> None:
    columns = ", ".join(_identifier(str(name)) for name in frame.columns)
    connection.register(INCOMING, frame)
    connection.execute(f"INSERT INTO {_identifier(table)} ({columns}) SELECT {columns} FROM {INCOMING}")  # noqa: S608 -- quoted names
    connection.unregister(INCOMING)


def _check_append(connection: duckdb.DuckDBPyConnection, table: str, frame: pd.DataFrame) -> None:
    known = {name.lower() for name in _columns(connection, table)}
    extra = [str(name) for name in frame.columns if str(name).lower() not in known]
    if extra:
        raise AppendRefused(f"table '{table}' has no column {', '.join(extra)}; append never changes the schema.")


class DuckdbAdapter(BaseAdapter):
    name = "duckdb"
    extensions = (".duckdb", ".db")
    options = ()
    appends = True
    first_part = "data"
    part_required = True

    def claims(self, path: Path) -> bool:
        with path.open("rb") as file:
            file.seek(SIGNATURE_OFFSET)
            return file.read(len(SIGNATURE)) == SIGNATURE

    def parts(self, path: Path) -> list[str]:
        with _connection(path, read_only=True) as connection:
            return _tables(connection)

    def row_counts(self, path: Path) -> dict[str, int]:
        with _connection(path, read_only=True) as connection:
            return {table: _count(connection, table) for table in _tables(connection)}

    def read_part(self, path: Path, part: str, options: ReadOptions) -> Loaded:
        with _connection(path, read_only=True) as connection:
            return Loaded(connection.execute(f"SELECT * FROM {_identifier(part)}").df(), infers_types=False)  # noqa: S608 -- quoted

    def query(self, path: Path, sql: str, options: ReadOptions) -> Loaded:
        with _connection(path, read_only=True) as connection:
            return Loaded(connection.execute(sql).df(), infers_types=False)

    def write_part(self, frame: pd.DataFrame, path: Path, part: str, options: WriteOptions) -> list[str]:
        with _transaction(path) as connection:
            if options.mode is Mode.APPEND and part in _tables(connection):
                _check_append(connection, part, frame)
            else:
                connection.execute(f"DROP TABLE IF EXISTS {_identifier(part)}")
                _create(connection, part, frame)
            _insert(connection, part, frame)
        return []


ADAPTER = DuckdbAdapter()
