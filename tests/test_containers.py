"""Containers: a file of named parts (sheets, tables), through the public library API and the CLI under --json.

The container is tests/data/containers/formats/zipcsv.py, a zip with one CSV per part,
added to the formats package the way tests/test_frame.py adds its probe format.
"""

from __future__ import annotations

import importlib
import json
import zipfile
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from rb_dataio import DataioError, backups, formats, info, read, restore, write
from rb_dataio.cli import app

# The package root's `formats` is the function; the formats package is reached through importlib.
format_modules = importlib.import_module("rb_dataio.formats")
FORMATS_FIXTURE = Path(__file__).parent / "data" / "containers" / "formats"
PART_A = b"x,y\n1,a\n2,b\n"
PART_B = b"x,y\n3,c\n"
runner = CliRunner()


def book(path: Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as file:
        for member, data in members.items():
            file.writestr(member, data)


def member(path: Path, name: str) -> bytes:
    with zipfile.ZipFile(path) as file:
        return file.read(name)


def invoke_json(*args: str) -> tuple[int, dict]:
    result = runner.invoke(app, [*args, "--json"])
    lines = result.stdout.splitlines()
    assert len(lines) == 1, f"stdout must be one JSON object; got {result.stdout!r}, stderr {result.stderr!r}"
    return result.exit_code, json.loads(lines[0])


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, data_dir: Path) -> Path:
    """The current directory with book.zcsv (parts A and B); the zipcsv format is known; the backup store is empty."""
    monkeypatch.setattr(format_modules, "__path__", [*format_modules.__path__, str(FORMATS_FIXTURE)])
    folder = tmp_path / "work"
    folder.mkdir()
    book(folder / "book.zcsv", {"A.csv": PART_A, "B.csv": PART_B})
    monkeypatch.chdir(folder)
    return folder


# --- read ------------------------------------------------------------------------


def test_the_fragment_names_the_part(workdir: Path) -> None:
    assert read("book.zcsv#B").to_dict("list") == {"x": [3], "y": ["c"]}


def test_the_sheet_parameter_names_the_part(workdir: Path) -> None:
    assert read("book.zcsv", sheet="B").to_dict("list") == {"x": [3], "y": ["c"]}


def test_no_part_named_reads_the_first(workdir: Path) -> None:
    assert read("book.zcsv").to_dict("list") == {"x": [1, 2], "y": ["a", "b"]}


def test_a_missing_part_is_source_not_found_listing_the_parts(workdir: Path) -> None:
    with pytest.raises(DataioError) as caught:
        read("book.zcsv#C")
    assert (caught.value.code, caught.value.exit_code) == ("SOURCE_NOT_FOUND", 2)
    assert "'C'" in caught.value.message
    assert caught.value.action == "Name one of the parts: A, B."


def test_star_stacks_the_parts_with_a_sheet_column_and_warns_about_other_columns(workdir: Path) -> None:
    book(workdir / "mixed.zcsv", {"A.csv": PART_A, "B.csv": b"x,z\n3,true\n"})
    frame = read("mixed.zcsv#*")
    assert list(frame.columns) == ["_sheet", "x", "y", "z"]
    assert frame.astype(object).where(frame.notna(), None).to_dict("list") == {
        "_sheet": ["A", "A", "B"],
        "x": [1, 2, 3],
        "y": ["a", "b", None],
        "z": [None, None, "true"],
    }
    code, payload = invoke_json("convert", "mixed.zcsv#*", "out.csv")
    assert code == 0
    assert payload["warnings"] == ["the parts have different columns: y, z; a part without one leaves it empty"]


def test_star_with_equal_columns_has_no_warning(workdir: Path) -> None:
    code, payload = invoke_json("convert", "book.zcsv#*", "out.csv")
    assert code == 0
    assert payload["warnings"] == []
    assert (workdir / "out.csv").read_text(encoding="utf-8") == "_sheet,x,y\nA,1,a\nA,2,b\nB,3,c\n"


# --- write -----------------------------------------------------------------------


def test_a_write_replaces_its_part_and_keeps_the_others(workdir: Path) -> None:
    report = write(pd.DataFrame({"x": [9], "y": ["z"]}), "book.zcsv#B")
    assert report.warnings == []
    assert read("book.zcsv#B").to_dict("list") == {"x": [9], "y": ["z"]}
    assert member(workdir / "book.zcsv", "A.csv") == PART_A
    [entry] = backups()
    assert entry.target == str(workdir / "book.zcsv")
    assert (entry.rows, entry.columns) == (1, ["x", "y"])
    restore()
    assert member(workdir / "book.zcsv", "B.csv") == PART_B
    assert member(workdir / "book.zcsv", "A.csv") == PART_A


def test_a_write_to_a_new_part_adds_it(workdir: Path) -> None:
    write(pd.DataFrame({"x": [5]}), "book.zcsv", sheet="C")
    assert read("book.zcsv#C").to_dict("list") == {"x": [5]}
    assert (member(workdir / "book.zcsv", "A.csv"), member(workdir / "book.zcsv", "B.csv")) == (PART_A, PART_B)


def test_a_write_to_a_new_file_makes_the_first_part(workdir: Path) -> None:
    write(pd.DataFrame({"x": [5]}), "new.zcsv")
    with zipfile.ZipFile(workdir / "new.zcsv") as file:
        assert file.namelist() == ["Sheet1.csv"]
    assert backups() == []


def test_the_warnings_of_the_adapter_write_reach_the_report(workdir: Path) -> None:
    book(workdir / "charts.zcsv", {"A.csv": PART_A, "chart.xml": b"<chart/>"})
    report = write(pd.DataFrame({"x": [9]}), "charts.zcsv#A")
    assert "charts may be lost" in report.warnings


# --- info / formats --------------------------------------------------------------


def test_info_json_lists_the_parts(workdir: Path) -> None:
    code, payload = invoke_json("info", "book.zcsv")
    assert code == 0
    assert payload["parts"] == ["A", "B"]


def test_info_of_a_csv_has_no_parts(workdir: Path) -> None:
    (workdir / "a.csv").write_text("x\n1\n", encoding="utf-8")
    code, payload = invoke_json("info", "a.csv")
    assert code == 0
    assert payload.get("parts", []) == []
    assert info("a.csv").parts == []


def test_a_helper_module_of_the_formats_package_is_no_format(workdir: Path) -> None:
    names = [entry.name for entry in formats()]
    assert "zipcsv" in names
    assert "_helpers" not in names


def test_info_human_output_names_the_parts(workdir: Path) -> None:
    result = runner.invoke(app, ["info", "book.zcsv"])
    assert result.exit_code == 0
    assert "Parts: A, B" in [line.strip() for line in result.stdout.splitlines()]
