"""Batch convert (DATAIO-020): many files one to one with {stem}, stop or keep going, dry-run and per-file backups.

The sources are copied from tests/data/batch/; the tests go through `convert()`, `backups()`, `restore()` and the CLI.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from rb_dataio import DataioError, backups, convert, read, restore
from rb_dataio.cli import app

DATA = Path(__file__).parent / "data" / "batch"
runner = CliRunner()


@pytest.fixture
def folder(tmp_path: Path, data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """`in/` with a.csv (2 rows), b.csv (broken) and c.csv (1 row); the work dir is `tmp_path`."""
    shutil.copytree(DATA, tmp_path / "in")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def two_good(folder: Path) -> None:
    (folder / "in" / "b.csv").write_text("x,y\n7,8\n9,10\n11,12\n", encoding="utf-8")


def invoke_json(*args: str) -> tuple[int, dict]:
    result = runner.invoke(app, [*args, "--json"])
    return result.exit_code, json.loads(result.stdout.splitlines()[0])


def test_each_source_goes_to_its_own_target(folder: Path) -> None:
    two_good(folder)
    code, payload = invoke_json("convert", "in/*.csv", "out/{stem}.xlsx")
    assert code == 0
    assert payload["ok"] is True
    assert payload["targets"] == [
        {"uri": "out/a.xlsx", "rows": 2},
        {"uri": "out/b.xlsx", "rows": 3},
        {"uri": "out/c.xlsx", "rows": 1},
    ]
    assert read("out/a.xlsx").to_dict("records") == [{"x": 1, "y": 2}, {"x": 3, "y": 4}]
    assert read("out/b.xlsx").to_dict("records") == [{"x": 7, "y": 8}, {"x": 9, "y": 10}, {"x": 11, "y": 12}]
    assert read("out/c.xlsx").to_dict("records") == [{"x": 5, "y": 6}]


def test_without_keep_going_the_run_stops_at_the_first_error(folder: Path) -> None:
    with pytest.raises(DataioError) as caught:
        convert("in/*.csv", "out/{stem}.xlsx")
    assert caught.value.code == "READ_FAILED"
    assert "in/b.csv" in caught.value.message
    assert (folder / "out" / "a.xlsx").exists()
    assert not (folder / "out" / "c.xlsx").exists()


def test_keep_going_writes_the_rest_and_lists_the_error(folder: Path) -> None:
    code, payload = invoke_json("convert", "in/*.csv", "out/{stem}.xlsx", "--keep-going")
    assert code == 1
    assert payload["ok"] is False
    assert payload["targets"] == [{"uri": "out/a.xlsx", "rows": 2}, {"uri": "out/c.xlsx", "rows": 1}]
    assert [(error["uri"], error["code"]) for error in payload["errors"]] == [("in/b.csv", "READ_FAILED")]
    assert "in/b.csv" in payload["errors"][0]["message"]
    assert (folder / "out" / "c.xlsx").exists()
    assert not (folder / "out" / "b.xlsx").exists()


def test_dry_run_lists_every_target_and_writes_nothing(folder: Path) -> None:
    two_good(folder)
    pd.DataFrame({"x": [1, 2, 3, 4, 5, 6, 7]}).to_excel(folder / "b.xlsx", index=False)
    (folder / "out").mkdir()
    shutil.move(folder / "b.xlsx", folder / "out" / "b.xlsx")
    before = (folder / "out" / "b.xlsx").read_bytes()
    code, payload = invoke_json("convert", "in/*.csv", "out/{stem}.xlsx", "--dry-run")
    assert code == 0
    assert payload["targets"] == [
        {"uri": "out/a.xlsx", "rows": 2, "exists": False, "rows_before": 0, "rows_after": 2},
        {"uri": "out/b.xlsx", "rows": 3, "exists": True, "rows_before": 7, "rows_after": 3},
        {"uri": "out/c.xlsx", "rows": 1, "exists": False, "rows_before": 0, "rows_after": 1},
    ]
    assert sorted(path.name for path in (folder / "out").iterdir()) == ["b.xlsx"]
    assert (folder / "out" / "b.xlsx").read_bytes() == before
    assert backups() == []


def test_every_replaced_file_has_its_own_backup(folder: Path) -> None:
    two_good(folder)
    (folder / "out").mkdir()
    (folder / "out" / "a.csv").write_text("old\n1\n", encoding="utf-8")
    (folder / "out" / "b.csv").write_text("old\n2\n3\n", encoding="utf-8")
    report = convert("in/*.csv", "out/{stem}.csv")
    assert report.targets is not None
    assert len(report.targets) == 3
    kept = backups()
    assert sorted(Path(entry.target).name for entry in kept) == ["a.csv", "b.csv"]
    for entry in kept:
        restore(entry.id)
    assert (folder / "out" / "a.csv").read_text(encoding="utf-8") == "old\n1\n"
    assert (folder / "out" / "b.csv").read_text(encoding="utf-8") == "old\n2\n3\n"


def test_a_mask_that_matches_nothing_is_source_not_found(folder: Path) -> None:
    with pytest.raises(DataioError) as caught:
        convert("in/*.json", "out/{stem}.xlsx")
    assert caught.value.code == "SOURCE_NOT_FOUND"
