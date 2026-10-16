"""SQLite bases: x.sqlite#table read and write with modes, transactions and concurrent appends.

Through the public library API and the CLI under --json, on base files the tests create with stdlib
sqlite3; the concurrency test runs two subprocesses (tests/data/sqlite/append_rows.py).
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from rb_dataio import DataioError, backups, read, restore, write
from rb_dataio.cli import app
from rb_dataio.formats import sqlite as sqlite_format

APPENDER = Path(__file__).parent / "data" / "sqlite" / "append_rows.py"
OLD = {"phrase": ["ёлка", "ель"], "freq": [5, 20]}
runner = CliRunner()


def make_base(path: Path, **tables: list[tuple]) -> None:
    with closing(sqlite3.connect(path)) as connection, connection:
        for name, rows in tables.items():
            connection.execute(f'CREATE TABLE "{name}" (phrase TEXT, freq INTEGER)')
            connection.executemany(f'INSERT INTO "{name}" VALUES (?, ?)', rows)  # noqa: S608 -- test names


def rows_of(path: Path, table: str = "t") -> list[tuple]:
    with closing(sqlite3.connect(path)) as connection:
        return connection.execute(f'SELECT * FROM "{table}"').fetchall()  # noqa: S608 -- test names


def integrity(path: Path) -> str:
    with closing(sqlite3.connect(path)) as connection:
        return connection.execute("PRAGMA integrity_check").fetchone()[0]


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, data_dir: Path) -> Path:
    """The current directory with x.sqlite: t (phrase, freq: 2 rows); the backup store is empty."""
    folder = tmp_path / "work"
    folder.mkdir()
    make_base(folder / "x.sqlite", t=[("ёлка", 5), ("ель", 20)])
    monkeypatch.chdir(folder)
    return folder


# --- read -----------------------------------------------------------------------


def test_a_table_is_read_by_the_fragment(workdir: Path) -> None:
    make_base(workdir / "x.sqlite3", t=[("a", 1)], u=[("b", 2)])
    assert read("x.sqlite#t").to_dict("list") == OLD
    assert read("x.sqlite3", table="u").to_dict("list") == {"phrase": ["b"], "freq": [2]}


def test_one_table_and_no_name_is_read(workdir: Path) -> None:
    assert read("x.sqlite").to_dict("list") == OLD


def test_several_tables_and_no_name_is_source_not_found_listing_them(workdir: Path) -> None:
    make_base(workdir / "y.sqlite", t=[("a", 1)], u=[("b", 2)])
    with pytest.raises(DataioError) as caught:
        read("y.sqlite")
    assert caught.value.code == "SOURCE_NOT_FOUND"
    assert "t, u" in (caught.value.action or "")


def test_a_db_file_of_stdlib_sqlite3_is_read(workdir: Path) -> None:
    make_base(workdir / "plain.db", t=[("a", 1)])
    assert read("plain.db").to_dict("list") == {"phrase": ["a"], "freq": [1]}


def test_a_query_runs_inside_the_base(workdir: Path) -> None:
    make_base(workdir / "y.sqlite", t=[("ёлка", 5), ("ель", 20)], u=[("b", 2)])
    frame = read("y.sqlite", query="select * from t where freq > 10")
    assert frame.to_dict("list") == {"phrase": ["ель"], "freq": [20]}
    assert read("y.sqlite", query="select count(*) as n from t, u").to_dict("list") == {"n": [2]}


# --- write ----------------------------------------------------------------------


def test_a_replace_swaps_the_table_and_restore_brings_back_the_old_rows(workdir: Path) -> None:
    write(pd.DataFrame({"phrase": ["сосна"], "freq": [9]}), "x.sqlite#t")
    assert rows_of(workdir / "x.sqlite") == [("сосна", 9)]
    [entry] = backups()
    assert (entry.table, entry.rows) == ("t", 2)
    restore(entry.id)
    assert read("x.sqlite#t").to_dict("list") == OLD


def test_types_are_stored_as_integer_real_text_and_timestamp(workdir: Path) -> None:
    frame = pd.DataFrame(
        {
            "i": [1, 2],
            "r": [0.5, None],
            "s": ["a", None],
            "d": pd.to_datetime(["2026-01-02 03:04:05", "2026-02-03 00:00:00"]),
        }
    )
    write(frame, "x.sqlite#typed")
    with closing(sqlite3.connect(workdir / "x.sqlite")) as connection:
        declared = [row[2] for row in connection.execute("PRAGMA table_info(typed)")]
    assert declared == ["INTEGER", "REAL", "TEXT", "TIMESTAMP"]
    back = read("x.sqlite#typed")
    assert back["d"].tolist() == list(pd.to_datetime(["2026-01-02 03:04:05", "2026-02-03 00:00:00"]))
    assert back["r"].isna().tolist() == [False, True]


def test_an_append_with_an_extra_column_is_write_failed_naming_it(workdir: Path) -> None:
    frame = pd.DataFrame({"phrase": ["x"], "freq": [1], "extra": [2]})
    with pytest.raises(DataioError) as caught:
        write(frame, "x.sqlite#t", mode="append")
    assert caught.value.code == "WRITE_FAILED"
    assert "extra" in str(caught.value)
    assert rows_of(workdir / "x.sqlite") == [("ёлка", 5), ("ель", 20)]


def test_an_append_with_a_missing_column_leaves_null(workdir: Path) -> None:
    write(pd.DataFrame({"phrase": ["x"]}), "x.sqlite#t", mode="append")
    assert rows_of(workdir / "x.sqlite") == [("ёлка", 5), ("ель", 20), ("x", None)]


def test_a_write_that_fails_after_half_the_rows_leaves_the_old_rows(
    workdir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def half(frame: pd.DataFrame) -> pd.DataFrame:
        class Failing(pd.DataFrame):
            def itertuples(self, *args: object, **kwargs: object) -> Iterator[tuple]:
                yield ("a", 1)
                raise OSError("disk full")

        return Failing(frame)

    monkeypatch.setattr(sqlite_format, "plain", half)
    with pytest.raises(DataioError) as caught:
        write(pd.DataFrame({"phrase": ["a", "b", "c", "d"], "freq": [1, 2, 3, 4]}), "x.sqlite#t")
    assert caught.value.code == "WRITE_FAILED"
    assert rows_of(workdir / "x.sqlite") == [("ёлка", 5), ("ель", 20)]


def test_two_processes_appending_at_once_keep_the_base_whole(workdir: Path) -> None:
    base = str(workdir / "x.sqlite")
    runs = [
        subprocess.Popen([sys.executable, str(APPENDER), base, tag], stdout=subprocess.PIPE, text=True)  # noqa: S603
        for tag in ("p", "q")
    ]
    refused = [out.strip() for run in runs for out in [run.communicate()[0]] if out.strip()]
    assert all(run.returncode == 0 for run in runs)
    assert set(refused) <= {"WRITE_FAILED"}
    added = len(rows_of(workdir / "x.sqlite")) - 2
    assert added == 2000 - 1000 * len(refused)
    assert integrity(workdir / "x.sqlite") == "ok"


# --- info / formats -------------------------------------------------------------


def invoke_json(*args: str) -> dict:
    result = runner.invoke(app, [*args, "--json"])
    assert result.exit_code == 0, result.stdout
    return json.loads(result.stdout)


def test_info_lists_the_tables_with_their_row_counts(workdir: Path) -> None:
    make_base(workdir / "y.sqlite", t=[("a", 1)], u=[("b", 2), ("c", 3)])
    assert invoke_json("info", "y.sqlite")["part_rows"] == {"t": 1, "u": 2}
    assert invoke_json("info", "y.sqlite#u")["part_rows"] == {"t": 1, "u": 2}


def test_formats_lists_sqlite_with_read_write_and_append(workdir: Path) -> None:
    [entry] = [entry for entry in invoke_json("formats")["formats"] if entry["name"] == "sqlite"]
    assert (entry["read"], entry["write"], entry["append"]) == (True, True, True)
    assert entry["extensions"] == [".sqlite", ".sqlite3", ".db"]
