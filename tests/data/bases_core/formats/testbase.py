"""A base format that tests/test_bases_core.py adds to the formats package: a stdlib sqlite3 file, `.tbase`.

Its parts are the tables, by name. `query` runs the SQL inside the base; a write
replaces or appends to one table in place, in one transaction.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import closing, contextmanager
from pathlib import Path

import pandas as pd

from rb_dataio.core.dataio.options import Mode, ReadOptions, WriteOptions
from rb_dataio.formats import BaseAdapter, Loaded
from rb_dataio.formats.json import plain


def _name(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


@contextmanager
def _transaction(path: Path) -> Generator[sqlite3.Connection]:
    with closing(sqlite3.connect(path, isolation_level=None)) as connection:
        connection.execute("BEGIN")
        try:
            yield connection
        except BaseException:
            connection.execute("ROLLBACK")
            raise
        connection.execute("COMMIT")


def _rows(path: Path, sql: str) -> pd.DataFrame:
    with closing(sqlite3.connect(path)) as connection:
        try:
            return pd.read_sql_query(sql, connection)
        except pd.errors.DatabaseError as exc:
            raise ValueError(str(exc)) from exc


class TbaseAdapter(BaseAdapter):
    name = "testbase"
    extensions = (".tbase",)
    options = ()
    appends = True
    first_part = "data"

    def parts(self, path: Path) -> list[str]:
        return _rows(path, "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")["name"].tolist()

    def row_counts(self, path: Path) -> dict[str, int]:
        counts = {part: _rows(path, f"SELECT COUNT(*) AS n FROM {_name(part)}") for part in self.parts(path)}  # noqa: S608
        return {part: int(frame["n"][0]) for part, frame in counts.items()}

    def read_part(self, path: Path, part: str, options: ReadOptions) -> Loaded:
        return Loaded(_rows(path, f"SELECT * FROM {_name(part)}"), infers_types=False)  # noqa: S608 -- a quoted name

    def query(self, path: Path, sql: str, options: ReadOptions) -> Loaded:
        return Loaded(_rows(path, sql), infers_types=False)

    def write_part(self, frame: pd.DataFrame, path: Path, part: str, options: WriteOptions) -> list[str]:
        with _transaction(path) as connection:
            if options.mode is not Mode.APPEND:
                connection.execute(f"DROP TABLE IF EXISTS {_name(part)}")
            columns = ", ".join(_name(str(column)) for column in frame.columns)
            connection.execute(f"CREATE TABLE IF NOT EXISTS {_name(part)} ({columns})")
            marks = ", ".join("?" * frame.shape[1])
            rows = plain(frame).itertuples(index=False, name=None)
            connection.executemany(f"INSERT INTO {_name(part)} VALUES ({marks})", rows)  # noqa: S608 -- a quoted name
        return []


ADAPTER = TbaseAdapter()
