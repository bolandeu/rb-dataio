"""Bases in the core: a table written in place in one transaction, its old rows kept as a backup, and formats told
apart by their signature; through the public library API and the human view of the CLI `backups`.

The base is tests/data/bases_core/formats/testbase.py (stdlib sqlite3, `.tbase`); alpha and beta
are two formats of `.db` files with their own signatures. They are added to the formats package the
way tests/test_containers.py adds its container.
"""

from __future__ import annotations

import importlib
import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from rb_dataio import DataioError, backups, read, restore, write
from rb_dataio.cli import app

format_modules = importlib.import_module("rb_dataio.formats")
FORMATS_FIXTURE = Path(__file__).parent / "data" / "bases_core" / "formats"


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, data_dir: Path) -> Path:
    """The current directory with base.tbase: t (phrase, freq: 2 rows) and u (n: 1 row); the backup store is empty."""
    monkeypatch.setattr(format_modules, "__path__", [*format_modules.__path__, str(FORMATS_FIXTURE)])
    folder = tmp_path / "work"
    folder.mkdir()
    with closing(sqlite3.connect(folder / "base.tbase")) as connection, connection:
        connection.execute("CREATE TABLE t (phrase TEXT, freq INTEGER)")
        connection.executemany("INSERT INTO t VALUES (?, ?)", [("ёлка", 5), ("ель", 2)])
        connection.execute("CREATE TABLE u (n INTEGER)")
        connection.execute("INSERT INTO u VALUES (1)")
    monkeypatch.chdir(folder)
    return folder


def test_a_replace_writes_the_table_in_place_and_restore_brings_back_its_old_rows(workdir: Path) -> None:
    base = workdir / "base.tbase"
    inode = base.stat().st_ino
    write(pd.DataFrame({"phrase": ["сосна"], "freq": [9]}), "base.tbase#t")
    assert base.stat().st_ino == inode, "the base was replaced by a copy"
    assert sorted(path.name for path in workdir.iterdir()) == ["base.tbase"]
    assert read("base.tbase#t").to_dict("list") == {"phrase": ["сосна"], "freq": [9]}
    [entry] = backups()
    assert (entry.target, entry.format, entry.table) == (str(base), "testbase", "t")
    assert (entry.rows, entry.columns) == (2, ["phrase", "freq"])

    write(pd.DataFrame({"n": [7, 8]}), "base.tbase#u", backup=False)
    restore(entry.id)
    assert base.stat().st_ino == inode
    assert read("base.tbase#t").to_dict("list") == {"phrase": ["ёлка", "ель"], "freq": [5, 2]}
    assert read("base.tbase#u").to_dict("list") == {"n": [7, 8]}, "the restore changed another table"


def test_restore_of_a_table_keeps_its_current_rows_first(workdir: Path) -> None:
    write(pd.DataFrame({"phrase": ["сосна"], "freq": [9]}), "base.tbase#t")
    restore()
    newest = backups()[0]
    assert (newest.table, newest.rows) == ("t", 1)
    restore(newest.id)
    assert read("base.tbase#t").to_dict("list") == {"phrase": ["сосна"], "freq": [9]}


def test_backups_human_output_names_the_table_of_each_entry(workdir: Path) -> None:
    write(pd.DataFrame({"phrase": ["сосна"], "freq": [9]}), "base.tbase#t")
    write(pd.DataFrame({"n": [7]}), "base.tbase#u")
    result = CliRunner().invoke(app, ["backups"], env={"COLUMNS": "400"})
    assert result.exit_code == 0
    targets = {line.split()[0]: line.split()[2] for line in result.stdout.splitlines()}
    base = workdir / "base.tbase"
    assert targets == {entry.id: f"{base}#{entry.table}" for entry in backups()}
    assert sorted(targets.values()) == [f"{base}#t", f"{base}#u"]


def test_a_new_table_keeps_no_backup_and_leaves_the_others(workdir: Path) -> None:
    write(pd.DataFrame({"n": [3]}), "base.tbase", table="v")
    assert backups() == []
    assert read("base.tbase#v").to_dict("list") == {"n": [3]}
    assert read("base.tbase#u").to_dict("list") == {"n": [1]}


def test_a_dry_run_of_a_table_reports_its_rows_and_writes_nothing(workdir: Path) -> None:
    report = write(pd.DataFrame({"phrase": ["сосна"], "freq": [9]}), "base.tbase#t", dry_run=True).to_dict()
    assert (report["target"]["exists"], report["target"]["rows_before"], report["target"]["rows_after"]) == (True, 2, 1)
    assert read("base.tbase#t")["freq"].tolist() == [5, 2]
    assert backups() == []


def test_a_query_runs_inside_the_base(workdir: Path) -> None:
    frame = read("base.tbase", query="select t.phrase, u.n from t, u where t.freq > 3")
    assert frame.to_dict("list") == {"phrase": ["ёлка"], "n": [1]}


# --- the signature --------------------------------------------------------------


def test_a_db_file_goes_to_the_format_whose_signature_it_has(workdir: Path) -> None:
    (workdir / "a.db").write_bytes(b"ALPHA\nx\n1\n")
    (workdir / "b.db").write_bytes(b"BETA\ny\n2\n")
    assert read("a.db").to_dict("list") == {"x": [1]}
    assert read("b.db").to_dict("list") == {"y": [2]}


def test_a_db_file_of_no_known_signature_is_format_unknown(workdir: Path) -> None:
    (workdir / "c.db").write_bytes(b"GAMMA\nz\n3\n")
    with pytest.raises(DataioError) as caught:
        read("c.db")
    assert (caught.value.code, caught.value.exit_code) == ("FORMAT_UNKNOWN", 2)
