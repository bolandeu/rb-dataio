"""Merging many sources into one table: globs, folders and lists, with `_source` and `_sheet`.

Integration tests through the public library API and the CLI under --json, on folders of small csv and xlsx
files the tests write.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from rb_dataio import DataioError, convert, read
from rb_dataio.cli import app

runner = CliRunner()


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def write_csv(path: str, text: str) -> None:
    file = Path(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text, encoding="utf-8")


def write_book(path: str, sheets: dict[str, pd.DataFrame]) -> None:
    file = Path(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(file) as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name, index=False)


def three_csv_files() -> None:
    write_csv("in/a.csv", "x,y\n1,2\n")
    write_csv("in/b.csv", "x,y\n3,4\n")
    write_csv("in/c.csv", "x,y\n5,6\n")


def test_a_glob_stacks_its_files_with_a_source_column(workdir: Path) -> None:
    three_csv_files()
    frame = read("in/*.csv", as_text=True)
    assert list(frame.columns) == ["_source", "x", "y"]
    assert frame.to_dict("records") == [
        {"_source": "in/a.csv", "x": "1", "y": "2"},
        {"_source": "in/b.csv", "x": "3", "y": "4"},
        {"_source": "in/c.csv", "x": "5", "y": "6"},
    ]


def test_source_column_none_leaves_the_column_out(workdir: Path) -> None:
    three_csv_files()
    frame = read("in/*.csv", source_column=None)
    assert list(frame.columns) == ["x", "y"]
    assert len(frame) == 3


def test_source_column_can_be_renamed(workdir: Path) -> None:
    three_csv_files()
    assert list(read("in/*.csv", source_column="file").columns) == ["file", "x", "y"]


def test_limit_applies_to_the_merged_table(workdir: Path) -> None:
    three_csv_files()
    assert len(read("in/*.csv", limit=2)) == 2


NESTED = {"in/a.xlsx": 1, "in/deep/b.xlsx": 2, "in/deep/er/c.xlsx": 3}


def write_nested_books() -> None:
    for path, value in NESTED.items():
        write_book(path, {"S": pd.DataFrame({"v": [value]})})


def test_a_recursive_glob_reads_nested_folders(workdir: Path) -> None:
    write_nested_books()
    frame = read("in/**/*.xlsx")
    assert sorted(frame["_source"]) == sorted(NESTED)
    assert sorted(frame["v"]) == [1, 2, 3]


def test_a_folder_path_merges_its_files(workdir: Path) -> None:
    three_csv_files()
    frame = read("in", as_text=True)
    assert frame["_source"].tolist() == ["in/a.csv", "in/b.csv", "in/c.csv"]
    assert frame["x"].tolist() == ["1", "3", "5"]


def test_a_list_of_addresses_merges_them(workdir: Path) -> None:
    three_csv_files()
    frame = read(["in/c.csv", "in/a.csv"], as_text=True)
    assert frame["_source"].tolist() == ["in/c.csv", "in/a.csv"]
    assert frame["x"].tolist() == ["5", "1"]


def test_a_list_may_mix_globs_and_files(workdir: Path) -> None:
    three_csv_files()
    write_csv("other.csv", "x,y\n9,9\n")
    frame = read(["in/*.csv", "other.csv"], as_text=True)
    assert frame["_source"].tolist() == ["in/a.csv", "in/b.csv", "in/c.csv", "other.csv"]


def test_a_list_of_plain_lines_is_still_the_text_column(workdir: Path) -> None:
    assert read(["apple", "pear"])["text"].tolist() == ["apple", "pear"]


def test_sheets_of_books_get_a_sheet_column_too(workdir: Path) -> None:
    for book, base in (("one", 10), ("two", 20)):
        write_book(
            f"reports/{book}.xlsx",
            {"north": pd.DataFrame({"v": [base]}), "south": pd.DataFrame({"v": [base + 1]})},
        )
    frame = read("reports/*.xlsx#*")
    assert list(frame.columns) == ["_source", "_sheet", "v"]
    assert frame.to_dict("records") == [
        {"_source": "reports/one.xlsx", "_sheet": "north", "v": 10},
        {"_source": "reports/one.xlsx", "_sheet": "south", "v": 11},
        {"_source": "reports/two.xlsx", "_sheet": "north", "v": 20},
        {"_source": "reports/two.xlsx", "_sheet": "south", "v": 21},
    ]


def different_columns() -> None:
    write_csv("in/a.csv", "a,b\n1,2\n")
    write_csv("in/b.csv", "a,c\n3,4\n")


def test_different_columns_are_a_union_with_one_warning(workdir: Path) -> None:
    different_columns()
    report = convert("in/*.csv", "out.json")
    assert report.target is not None
    assert report.target.columns == ["_source", "a", "b", "c"]
    assert len(report.warnings) == 1
    assert "b, c" in report.warnings[0]
    frame = read("in/*.csv", as_text=True)
    assert list(frame.columns) == ["_source", "a", "b", "c"]
    assert frame["b"].tolist()[0] == "2"
    assert pd.isna(frame["b"].tolist()[1])
    assert pd.isna(frame["c"].tolist()[0])
    assert frame["c"].tolist()[1] == "4"


def test_strict_lists_the_columns_of_each_file(workdir: Path) -> None:
    different_columns()
    with pytest.raises(DataioError) as caught:
        read("in/*.csv", strict=True)
    assert caught.value.code == "SCHEMA_MISMATCH"
    assert caught.value.exit_code == 2
    assert "in/a.csv (a, b)" in caught.value.message
    assert "in/b.csv (a, c)" in caught.value.message


def test_strict_passes_when_the_columns_agree(workdir: Path) -> None:
    three_csv_files()
    assert len(read("in/*.csv", strict=True)) == 3


def test_a_glob_that_matches_nothing_is_source_not_found(workdir: Path) -> None:
    with pytest.raises(DataioError) as caught:
        read("in/*.csv")
    assert caught.value.code == "SOURCE_NOT_FOUND"
    assert "in/*.csv" in caught.value.message


def test_a_missing_file_in_a_list_is_source_not_found(workdir: Path) -> None:
    three_csv_files()
    with pytest.raises(DataioError) as caught:
        read(["in/a.csv", "in/nope.csv"])
    assert caught.value.code == "SOURCE_NOT_FOUND"
    assert "in/nope.csv" in caught.value.message


def test_the_cli_merges_a_glob_and_reports_the_source(workdir: Path) -> None:
    three_csv_files()
    result = runner.invoke(app, ["convert", "in/*.csv", "out.csv", "--json"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout.splitlines()[0])
    assert payload["source"]["rows"] == 3
    assert payload["source"]["columns"] == ["_source", "x", "y"]
    assert Path("out.csv").read_text(encoding="utf-8").splitlines()[0] == "_source,x,y"


def test_the_cli_strict_is_exit_2(workdir: Path) -> None:
    different_columns()
    result = runner.invoke(app, ["convert", "in/*.csv", "out.csv", "--strict", "--json"])
    assert result.exit_code == 2
    assert json.loads(result.stdout.splitlines()[0])["error"]["code"] == "SCHEMA_MISMATCH"
