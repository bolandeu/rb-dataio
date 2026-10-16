"""SQLite: a base of tables, through the stdlib sqlite3 (ADR 0002); the table is the address fragment or `table=`.

The format covers `.sqlite`, `.sqlite3` and `.db` (a `.db` file is claimed by the SQLite signature). With no
table named, a base of one table reads that table; a base of several is SOURCE_NOT_FOUND, which lists
them. `query=` runs inside the base. A write stores each column as INTEGER, REAL, TEXT or TIMESTAMP (the
text of the date). A write is one transaction taken before any change (`BEGIN IMMEDIATE`) that waits
for another writer: a replace drops and creates the table, an append adds rows and refuses a column the
table lacks (a column the frame lacks is NULL), and a write that fails leaves the base as it was.
A read gives a TIMESTAMP column back as dates and every other column as stored.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import closing, contextmanager
from pathlib import Path

import pandas as pd

from ..core.dataio.options import Mode, ReadOptions, WriteOptions
from . import BaseAdapter, Loaded
from .json import plain

SIGNATURE = b"SQLite format 3\x00"
WAIT_SECONDS = 30  # how long a read or a write waits for another process that holds the base
TIMESTAMP = "TIMESTAMP"


def _name(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


@contextmanager
def _connection(path: Path) -> Generator[sqlite3.Connection]:
    """A connection with no implicit transactions; an error of the database is a ValueError with its message."""
    try:
        with closing(sqlite3.connect(path, timeout=WAIT_SECONDS, isolation_level=None)) as connection:
            yield connection
    except sqlite3.Error as exc:
        raise ValueError(str(exc)) from exc


@contextmanager
def _transaction(path: Path) -> Generator[sqlite3.Connection]:
    with _connection(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            yield connection
        except BaseException:
            connection.execute("ROLLBACK")
            raise
        connection.execute("COMMIT")


def _select(path: Path, sql: str) -> pd.DataFrame:
    with _connection(path) as connection:
        return pd.read_sql_query(sql, connection)


def _declared(connection: sqlite3.Connection, table: str) -> dict[str, str]:
    """The columns of `table` with their declared types; empty when the base has no such table."""
    return {row[1]: row[2].upper() for row in connection.execute(f"PRAGMA table_info({_name(table)})")}


def _type_of(dtype: object) -> str:
    if pd.api.types.is_bool_dtype(dtype) or pd.api.types.is_integer_dtype(dtype):
        return "INTEGER"
    if pd.api.types.is_float_dtype(dtype):
        return "REAL"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return TIMESTAMP
    return "TEXT"


def _bindable(frame: pd.DataFrame) -> pd.DataFrame:
    """The table with values sqlite3 binds: a date is its ISO text, a missing value is None."""
    dates = {
        column: frame[column].dt.strftime("%Y-%m-%d %H:%M:%S")
        for column in frame
        if _type_of(frame[column].dtype) == TIMESTAMP
    }
    return plain(frame.assign(**dates))


def _require_known_columns(frame: pd.DataFrame, declared: dict[str, str], table: str) -> None:
    extra = [str(column) for column in frame.columns if str(column) not in declared]
    if extra:
        raise ValueError(
            f"the table '{table}' has no column {', '.join(repr(name) for name in extra)}: an append does not change its schema."
        )


class SqliteAdapter(BaseAdapter):
    name = "sqlite"
    extensions = (".sqlite", ".sqlite3", ".db")
    options = ()
    appends = True
    first_part = "data"
    part_required = True

    def claims(self, path: Path) -> bool:
        with path.open("rb") as file:
            return file.read(len(SIGNATURE)) == SIGNATURE

    def parts(self, path: Path) -> list[str]:
        sql = "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        return _select(path, sql)["name"].tolist()

    def row_counts(self, path: Path) -> dict[str, int]:
        with _connection(path) as connection:
            return {
                part: connection.execute(f"SELECT COUNT(*) FROM {_name(part)}").fetchone()[0]  # noqa: S608 -- a quoted name
                for part in self.parts(path)
            }

    def read_part(self, path: Path, part: str, options: ReadOptions) -> Loaded:
        with _connection(path) as connection:
            declared = _declared(connection, part)
            frame = pd.read_sql_query(f"SELECT * FROM {_name(part)}", connection)  # noqa: S608 -- a quoted name
        for column in frame.columns:
            if declared.get(str(column)) == TIMESTAMP:
                frame[column] = pd.to_datetime(frame[column], format="ISO8601")
        return Loaded(frame, infers_types=False)

    def query(self, path: Path, sql: str, options: ReadOptions) -> Loaded:
        try:
            return Loaded(_select(path, sql), infers_types=False)
        except pd.errors.DatabaseError as exc:
            raise ValueError(str(exc)) from exc

    def write_part(self, frame: pd.DataFrame, path: Path, part: str, options: WriteOptions) -> list[str]:
        columns = [str(column) for column in frame.columns]
        with _transaction(path) as connection:
            declared = _declared(connection, part)
            if options.mode is Mode.APPEND and declared:
                _require_known_columns(frame, declared, part)
            else:
                connection.execute(f"DROP TABLE IF EXISTS {_name(part)}")
                typed = ", ".join(
                    f"{_name(name)} {_type_of(dtype)}" for name, dtype in zip(columns, frame.dtypes, strict=True)
                )
                connection.execute(f"CREATE TABLE {_name(part)} ({typed})")
            names = ", ".join(_name(name) for name in columns)
            marks = ", ".join("?" * len(columns))
            rows = _bindable(frame).itertuples(index=False, name=None)
            connection.executemany(f"INSERT INTO {_name(part)} ({names}) VALUES ({marks})", rows)  # noqa: S608 -- quoted names
        return []


ADAPTER = SqliteAdapter()
