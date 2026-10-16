"""DuckDB bases: x.duckdb#table read and written with modes and transactions; the library API and the CLI under --json.

The bases are made by the duckdb package in temporary folders; a held base is made by a second process.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb
import pandas as pd
import pytest
from typer.testing import CliRunner

from rb_dataio import DataioError, backups, read, restore, write
from rb_dataio.cli import app
from rb_dataio.formats import duckdb as duckdb_format

runner = CliRunner()
HOLDER = (
    "import duckdb, sys\n"
    "connection = duckdb.connect(sys.argv[1], read_only=True)\n"
    "print('ready', flush=True)\n"
    "sys.stdin.readline()\n"
)


def make_base(path: Path, **tables: list[tuple]) -> None:
    """A base with the tables `name=[(phrase, freq), ...]`."""
    with duckdb.connect(str(path)) as connection:
        for name, rows in tables.items():
            connection.execute(f'CREATE TABLE "{name}" (phrase VARCHAR, freq BIGINT)')
            for row in rows:
                connection.execute(f'INSERT INTO "{name}" VALUES (?, ?)', list(row))  # noqa: S608 -- test names


def rows(path: Path, table: str) -> list[tuple]:
    with duckdb.connect(str(path), read_only=True) as connection:
        return connection.execute(f'SELECT * FROM "{table}"').fetchall()  # noqa: S608 -- test names


def invoke_json(*args: str) -> tuple[int, dict]:
    result = runner.invoke(app, [*args, "--json"])
    lines = result.stdout.splitlines()
    assert len(lines) == 1, f"stdout must be one JSON object; got {result.stdout!r}, stderr {result.stderr!r}"
    return result.exit_code, json.loads(lines[0])


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, data_dir: Path) -> Path:
    """The current directory with x.duckdb: t (phrase, freq: 3 rows); the backup store is empty."""
    folder = tmp_path / "work"
    folder.mkdir()
    make_base(folder / "x.duckdb", t=[("ёлка", 5), ("ель", 20), ("сосна", 30)])
    monkeypatch.chdir(folder)
    return folder


# --- read ------------------------------------------------------------------------


def test_a_table_is_read_by_the_fragment_and_with_one_table_by_no_name(workdir: Path) -> None:
    expected = {"phrase": ["ёлка", "ель", "сосна"], "freq": [5, 20, 30]}
    assert read("x.duckdb#t").to_dict("list") == expected
    assert read("x.duckdb").to_dict("list") == expected
    assert read("x.duckdb", table="t").to_dict("list") == expected


def test_several_tables_and_no_name_is_source_not_found_listing_them(workdir: Path) -> None:
    make_base(workdir / "y.duckdb", t=[("a", 1)], u=[("b", 2)])
    with pytest.raises(DataioError) as caught:
        read("y.duckdb")
    assert caught.value.code == "SOURCE_NOT_FOUND"
    assert "t, u" in str(caught.value.action)
    assert read("y.duckdb#u").to_dict("list") == {"phrase": ["b"], "freq": [2]}


def test_a_db_file_made_by_duckdb_is_read_by_this_format(workdir: Path) -> None:
    (workdir / "x.duckdb").rename(workdir / "x.db")
    assert read("x.db#t")["freq"].tolist() == [5, 20, 30]
    write(pd.DataFrame({"n": [1]}), "x.db#v")
    assert rows(workdir / "x.db", "v") == [(1,)]


def test_a_query_runs_inside_the_base(workdir: Path) -> None:
    make_base(workdir / "y.duckdb", t=[("a", 1), ("b", 11)], u=[("c", 2)])
    frame = read("y.duckdb", query="select t.phrase, u.freq from t, u where t.freq > 10")
    assert frame.to_dict("list") == {"phrase": ["b"], "freq": [2]}
    assert read("x.duckdb", query="select * from t where freq > 10")["phrase"].tolist() == ["ель", "сосна"]


# --- write -----------------------------------------------------------------------


def test_a_replace_swaps_the_table_and_restore_brings_back_the_old_rows(workdir: Path) -> None:
    write(pd.DataFrame({"phrase": ["пихта"], "freq": [7]}), "x.duckdb#t")
    assert rows(workdir / "x.duckdb", "t") == [("пихта", 7)]
    [entry] = backups()
    assert (entry.table, entry.rows) == ("t", 3)
    restore(entry.id)
    assert rows(workdir / "x.duckdb", "t") == [("ёлка", 5), ("ель", 20), ("сосна", 30)]


def test_the_types_of_the_columns_are_kept_in_the_base(workdir: Path) -> None:
    frame = pd.DataFrame(
        {
            "i": [1, 2],
            "f": [1.5, None],
            "s": ["a", None],
            "d": pd.to_datetime(["2024-01-02 03:04:05", None]),
        }
    )
    write(frame, "x.duckdb#v")
    with duckdb.connect(str(workdir / "x.duckdb"), read_only=True) as connection:
        described = connection.execute("DESCRIBE v").fetchall()
    assert [(name, kind) for name, kind, *_ in described] == [
        ("i", "BIGINT"),
        ("f", "DOUBLE"),
        ("s", "VARCHAR"),
        ("d", "TIMESTAMP"),
    ]
    assert rows(workdir / "x.duckdb", "v")[1] == (2, None, None, None)


def test_an_append_adds_rows_a_missing_column_is_null_an_extra_one_is_refused(workdir: Path) -> None:
    base = workdir / "x.duckdb"
    write(pd.DataFrame({"phrase": ["пихта"]}), "x.duckdb#t", mode="append")
    assert rows(base, "t")[-1] == ("пихта", None)
    with pytest.raises(DataioError) as caught:
        write(pd.DataFrame({"phrase": ["лиственница"], "color": ["green"]}), "x.duckdb#t", mode="append")
    assert caught.value.code == "WRITE_FAILED"
    assert "color" in str(caught.value)
    assert len(rows(base, "t")) == 4, "the refused append changed the table"
    assert backups() == []


def test_a_write_that_fails_midway_leaves_the_old_rows(workdir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original = duckdb_format._insert

    def half_then_fail(connection: duckdb.DuckDBPyConnection, table: str, frame: pd.DataFrame) -> None:
        original(connection, table, frame.head(len(frame) // 2))
        raise ValueError("disk full")

    monkeypatch.setattr(duckdb_format, "_insert", half_then_fail)
    for mode in ("replace", "append"):
        with pytest.raises(DataioError) as caught:
            write(pd.DataFrame({"phrase": ["a", "b", "c", "d"], "freq": [1, 2, 3, 4]}), "x.duckdb#t", mode=mode)
        assert caught.value.code == "WRITE_FAILED"
        assert rows(workdir / "x.duckdb", "t") == [("ёлка", 5), ("ель", 20), ("сосна", 30)]


def test_a_base_held_by_another_process_refuses_the_write_with_the_action_and_stays_whole(workdir: Path) -> None:
    base = workdir / "x.duckdb"
    holder = subprocess.Popen(  # noqa: S603 -- our own interpreter and script
        [sys.executable, "-I", "-c", HOLDER, str(base)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert holder.stdout is not None
        assert holder.stdout.readline().strip() == "ready"
        with pytest.raises(DataioError) as caught:
            write(pd.DataFrame({"phrase": ["a"], "freq": [1]}), "x.duckdb#t")
        assert caught.value.code == "WRITE_FAILED"
        assert "Close the other connection" in str(caught.value.action)
    finally:
        holder.communicate("\n")
    assert rows(base, "t") == [("ёлка", 5), ("ель", 20), ("сосна", 30)]


def test_a_write_with_a_read_connection_open_in_this_process_succeeds_or_asks_to_close_it(workdir: Path) -> None:
    base = workdir / "x.duckdb"
    with duckdb.connect(str(base), read_only=True) as other:
        other.execute("SELECT * FROM t").fetchall()
        try:
            write(pd.DataFrame({"phrase": ["a"], "freq": [1]}), "x.duckdb#t")
        except DataioError as exc:
            assert exc.code == "WRITE_FAILED"
            assert "Close the other connection" in str(exc.action)
            expected = [("ёлка", 5), ("ель", 20), ("сосна", 30)]
        else:
            expected = [("a", 1)]
    assert rows(base, "t") == expected


# --- info and formats ------------------------------------------------------------


def test_info_lists_the_tables_with_their_row_counts(workdir: Path) -> None:
    make_base(workdir / "y.duckdb", t=[("a", 1), ("b", 2)], u=[("c", 3)])
    code, payload = invoke_json("info", "y.duckdb")
    assert code == 0
    assert payload["parts"] == ["t", "u"]
    assert payload["part_rows"] == {"t": 2, "u": 1}
    code, payload = invoke_json("info", "y.duckdb#u")
    assert (code, payload["part_rows"]) == (0, {"t": 2, "u": 1})


def test_formats_lists_duckdb_with_read_write_and_append(workdir: Path) -> None:
    code, payload = invoke_json("formats")
    assert code == 0
    [entry] = [entry for entry in payload["formats"] if entry["name"] == "duckdb"]
    assert (entry["read"], entry["write"], entry["append"]) == (True, True, True)
    assert entry["extensions"] == [".duckdb", ".db"]
