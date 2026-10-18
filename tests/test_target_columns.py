"""Target columns: `columns` (keep, in order) and `rename` (old -> new) shape the table every target gets."""

from __future__ import annotations

import json
from pathlib import Path

import openpyxl
import pandas as pd
import pytest

from rb_dataio import DataioError, convert, read, write

TABLE = pd.DataFrame({"a": ["1", "2"], "b": ["3", "4"], "c": ["5", "6"]})


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, data_dir: Path) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_columns_keep_and_order(workdir: Path) -> None:
    write(TABLE, "out.csv", columns=["c", "a"])

    assert (workdir / "out.csv").read_text() == "c,a\n5,1\n6,2\n"


def test_rename_keeps_source_order_in_jsonl(workdir: Path) -> None:
    write(TABLE[["a", "b"]], "out.jsonl", rename={"b": "x"})

    lines = (workdir / "out.jsonl").read_text().splitlines()
    assert [list(json.loads(line)) for line in lines] == [["a", "x"], ["a", "x"]]


def test_selection_comes_before_rename(workdir: Path) -> None:
    report = write(TABLE, "out.csv", columns=["b", "a"], rename={"b": "x"})

    assert (workdir / "out.csv").read_text() == "x,a\n3,1\n4,2\n"
    assert report.target.columns == ["x", "a"]


@pytest.mark.parametrize(
    ("arguments", "named"),
    [
        ({"columns": ["a", "zz"]}, "zz"),
        ({"rename": {"zz": "x"}}, "zz"),
        ({"columns": ["a"], "rename": {"b": "x"}}, "b"),
    ],
)
def test_wrong_name_is_refused_and_nothing_is_written(workdir: Path, arguments: dict, named: str) -> None:
    with pytest.raises(DataioError) as refused:
        write(TABLE[["a", "b"]], "out.csv", **arguments)

    assert (refused.value.code, refused.value.exit_code) == ("INVALID_ARGUMENTS", 2)
    assert named in refused.value.message
    assert "a" in refused.value.message
    assert not (workdir / "out.csv").exists()


def test_wrong_column_lists_the_columns_there_are(workdir: Path) -> None:
    with pytest.raises(DataioError) as refused:
        write(TABLE[["a", "b"]], "out.csv", columns=["a", "zz"])

    assert "a, b" in refused.value.message


@pytest.mark.parametrize("rename", [{"a": "x", "b": "x"}, {"a": "b"}])
def test_clash_is_refused(workdir: Path, rename: dict) -> None:
    with pytest.raises(DataioError) as refused:
        write(TABLE[["a", "b"]], "out.csv", rename=rename)

    assert (refused.value.code, refused.value.exit_code) == ("INVALID_ARGUMENTS", 2)
    assert ("x" if "x" in rename.values() else "b") in refused.value.message
    assert not (workdir / "out.csv").exists()


def test_swap_is_accepted(workdir: Path) -> None:
    write(TABLE[["a", "b"]], "out.csv", rename={"a": "b", "b": "a"})

    assert (workdir / "out.csv").read_text() == "b,a\n1,3\n2,4\n"


def test_append_with_the_same_target_header(workdir: Path) -> None:
    (workdir / "out.csv").write_text("x,a\n0,0\n")

    write(TABLE, "out.csv", mode="append", columns=["b", "a"], rename={"b": "x"})

    assert (workdir / "out.csv").read_text() == "x,a\n0,0\n3,1\n4,2\n"


def test_append_with_another_header_is_refused_as_before(workdir: Path) -> None:
    (workdir / "out.csv").write_text("x,y\n0,0\n")

    with pytest.raises(DataioError):
        write(TABLE, "out.csv", mode="append", columns=["b", "a"], rename={"b": "x"})

    assert (workdir / "out.csv").read_text() == "x,y\n0,0\n"


def test_records_hold_the_target_columns() -> None:
    assert write(TABLE[["a", "b"]], format="records", columns=["a"], rename={"a": "x"}) == [{"x": "1"}, {"x": "2"}]


def test_wrong_name_is_refused_for_records() -> None:
    with pytest.raises(DataioError) as refused:
        write(TABLE, columns=["zz"])

    assert refused.value.exit_code == 2


@pytest.mark.parametrize("name", ["out.xlsx", "out.json", "out.parquet"])
def test_every_file_format_gets_the_target_columns(workdir: Path, name: str) -> None:
    write(TABLE, name, columns=["b", "a"], rename={"b": "x"})

    frame = read(name)
    assert list(frame.columns) == ["x", "a"]
    assert frame["x"].astype(str).tolist() == ["3", "4"]


def test_xlsx_header_row(workdir: Path) -> None:
    write(TABLE, "out.xlsx", columns=["b", "a"], rename={"b": "x"})

    sheet = openpyxl.load_workbook(workdir / "out.xlsx").active
    assert [cell.value for cell in sheet[1]] == ["x", "a"]


def test_stdout_gets_the_target_columns(capfd: pytest.CaptureFixture[str]) -> None:
    write(TABLE, "-", format="csv", columns=["b", "a"], rename={"b": "x"})

    assert capfd.readouterr().out == "x,a\n3,1\n4,2\n"


def test_convert_shapes_the_target(workdir: Path) -> None:
    (workdir / "in.csv").write_text("a,b,c\n1,3,5\n")

    convert("in.csv", "out.json", columns=["c", "a"], rename={"c": "z"})

    assert json.loads((workdir / "out.json").read_text()) == [{"z": 5, "a": 1}]


def test_without_both_arguments_the_output_is_unchanged(workdir: Path) -> None:
    write(TABLE, "plain.csv")
    write(TABLE, "same.csv", columns=None, rename=None)

    assert (workdir / "plain.csv").read_text() == (workdir / "same.csv").read_text() == "a,b,c\n1,3,5\n2,4,6\n"
    assert write(TABLE) == write(TABLE, columns=None, rename=None) == TABLE.to_dict("records")
