"""Excel books through the public library API and the CLI under --json.

The xlsx books are built here with openpyxl; book.xls, book.xlsb and book.ods in
tests/data/excel are tiny fixtures with the sheets First (code '007', '042'; amount 1, 2.5)
and Second.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import openpyxl
import pandas as pd
import pytest
from openpyxl.chart import BarChart, Reference
from typer.testing import CliRunner

from rb_dataio import DataioError, backups, read, write
from rb_dataio.cli import app
from rb_dataio.formats import xlsx

EXCEL_DATA = Path(__file__).parent / "data" / "excel"
runner = CliRunner()


def invoke_json(*args: str) -> tuple[int, dict]:
    result = runner.invoke(app, [*args, "--json"])
    lines = result.stdout.splitlines()
    assert len(lines) == 1, f"stdout must be one JSON object; got {result.stdout!r}, stderr {result.stderr!r}"
    return result.exit_code, json.loads(lines[0])


def build_book(path: Path, sheets: dict[str, list[tuple]]) -> None:
    book = openpyxl.Workbook()
    book.remove(book.active)
    for name, rows in sheets.items():
        sheet = book.create_sheet(name)
        for row in rows:
            sheet.append(row)
    book.save(path)


def sheet_rows(path: Path, name: str) -> list[tuple]:
    return list(openpyxl.load_workbook(path)[name].iter_rows(values_only=True))


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, data_dir: Path) -> Path:
    """The current directory with book.xlsx (sheets A and B); the backup store is empty."""
    folder = tmp_path / "work"
    folder.mkdir()
    build_book(folder / "book.xlsx", {"A": [("x", "y"), (1, "a"), (2, "b")], "B": [("x", "y"), (3, "c")]})
    monkeypatch.chdir(folder)
    return folder


# --- read ------------------------------------------------------------------------


def test_the_fragment_names_the_sheet(workdir: Path) -> None:
    assert read("book.xlsx#B").to_dict("list") == {"x": [3], "y": ["c"]}


def test_no_sheet_named_reads_the_first(workdir: Path) -> None:
    assert read("book.xlsx").to_dict("list") == {"x": [1, 2], "y": ["a", "b"]}


def test_a_missing_sheet_is_source_not_found_listing_the_sheets(workdir: Path) -> None:
    with pytest.raises(DataioError) as caught:
        read("book.xlsx#C")
    assert caught.value.code == "SOURCE_NOT_FOUND"
    assert caught.value.action == "Name one of the parts: A, B."


@pytest.mark.parametrize("extension", ["xls", "xlsb", "ods"])
def test_other_books_read_the_first_sheet_with_text_and_numbers(extension: str) -> None:
    frame = read(EXCEL_DATA / f"book.{extension}")
    assert frame.to_dict("list") == {"code": ["007", "042"], "amount": [1, 2.5]}
    assert pd.api.types.is_string_dtype(frame["code"])
    assert pd.api.types.is_numeric_dtype(frame["amount"])


@pytest.mark.parametrize("extension", ["xls", "xlsb", "ods"])
def test_other_books_read_a_named_sheet_with_whole_numbers(extension: str) -> None:
    frame = read(EXCEL_DATA / f"book.{extension}", sheet="Second")
    assert frame["x"].tolist() == [1]
    assert str(frame["x"].dtype) == "int64"


def test_cell_types_are_kept_and_empty_cells_are_missing(workdir: Path) -> None:
    build_book(
        workdir / "types.xlsx",
        {"S": [("id", "n", "word", "flag"), ("0012345678901234567", 1, "a", True), ("12", None, None, False)]},
    )
    frame = read("types.xlsx")
    assert frame["id"].tolist() == ["0012345678901234567", "12"]
    assert frame["n"].tolist()[0] == 1 and pd.isna(frame["n"][1])
    assert frame["word"].tolist()[0] == "a" and pd.isna(frame["word"][1])
    assert frame["flag"].tolist() == [True, False]


def test_without_header_the_columns_are_numbered(workdir: Path) -> None:
    assert read("book.xlsx#B", header=False).to_dict("list") == {"col1": ["x", 3], "col2": ["y", "c"]}


# --- write -----------------------------------------------------------------------


def test_a_write_replaces_its_sheet_and_keeps_the_others(workdir: Path) -> None:
    write(pd.DataFrame({"x": [9], "y": ["z"]}), "book.xlsx#B")
    assert openpyxl.load_workbook(workdir / "book.xlsx").sheetnames == ["A", "B"]
    assert sheet_rows(workdir / "book.xlsx", "B") == [("x", "y"), (9, "z")]
    assert sheet_rows(workdir / "book.xlsx", "A") == [("x", "y"), (1, "a"), (2, "b")]
    [entry] = backups()
    assert entry.target == str(workdir / "book.xlsx")


def test_a_new_book_has_sheet1_with_a_usable_layout(workdir: Path) -> None:
    write(pd.DataFrame({"name": ["a", "longer value"], "n": [1, 22]}), "new.xlsx")
    book = openpyxl.load_workbook(workdir / "new.xlsx")
    assert book.sheetnames == ["Sheet1"]
    sheet = book["Sheet1"]
    assert sheet.freeze_panes == "A2"
    assert sheet.auto_filter.ref == "A1:B3"
    assert sheet.column_dimensions["A"].width == 14  # 'longer value', 12 characters, and 2 of padding
    assert sheet.column_dimensions["B"].width == 4  # '22', 2 characters, and 2 of padding
    assert backups() == []


def test_missing_values_are_empty_cells(workdir: Path) -> None:
    write(pd.DataFrame({"n": pd.array([1, None], dtype="Int64"), "s": [None, "b"]}), "new.xlsx")
    assert sheet_rows(workdir / "new.xlsx", "Sheet1") == [("n", "s"), (1, None), (None, "b")]


@pytest.mark.parametrize("part", ["xl/charts/chart1.xml", "xl/pivotTables/pivotTable1.xml"])
def test_a_book_with_charts_or_pivot_tables_warns(workdir: Path, part: str) -> None:
    with zipfile.ZipFile(workdir / "book.xlsx", "a") as book:
        book.writestr(part, "<x/>")
    report = write(pd.DataFrame({"x": [9]}), "book.xlsx#B")
    assert "the book has charts or pivot tables: they may be lost" in report.warnings


def test_a_book_with_a_real_chart_warns(workdir: Path) -> None:
    book = openpyxl.load_workbook(workdir / "book.xlsx")
    chart = BarChart()
    chart.add_data(Reference(book["A"], min_col=1, min_row=1, max_row=3), titles_from_data=True)
    book["A"].add_chart(chart, "D2")
    book.save(workdir / "book.xlsx")
    report = write(pd.DataFrame({"x": [9]}), "book.xlsx#B")
    assert "the book has charts or pivot tables: they may be lost" in report.warnings


def test_a_book_without_charts_has_no_warning(workdir: Path) -> None:
    assert write(pd.DataFrame({"x": [9], "y": ["z"]}), "book.xlsx#B").warnings == []


def test_too_many_rows_are_refused_before_the_write(workdir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(xlsx, "MAX_ROWS", 3)  # the header and 2 rows fit, a third row does not
    write(pd.DataFrame({"x": [1, 2]}), "fits.xlsx")
    with pytest.raises(DataioError) as caught:
        write(pd.DataFrame({"x": [1, 2, 3]}), "big.xlsx")
    assert caught.value.code == "WRITE_FAILED"
    assert caught.value.action == "Write csv or parquet: they have no row limit."
    assert not (workdir / "big.xlsx").exists()


def test_appended_rows_count_toward_the_limit(workdir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(xlsx, "MAX_ROWS", 3)
    before = (workdir / "book.xlsx").read_bytes()
    with pytest.raises(DataioError) as caught:
        write(pd.DataFrame({"x": [4], "y": ["d"]}), "book.xlsx#A", mode="append")
    assert caught.value.code == "WRITE_FAILED"
    assert (workdir / "book.xlsx").read_bytes() == before


@pytest.mark.parametrize("extension", ["xls", "xlsb", "ods"])
def test_writing_other_books_is_refused_naming_xlsx(workdir: Path, extension: str) -> None:
    with pytest.raises(DataioError) as caught:
        write(pd.DataFrame({"x": [1]}), f"out.{extension}")
    assert caught.value.code == "FORMAT_UNSUPPORTED"
    assert caught.value.action == "Use xlsx instead: it is the format of this kind that can write."
    assert not (workdir / f"out.{extension}").exists()


def test_append_with_the_same_header_adds_rows_below(workdir: Path) -> None:
    report = write(pd.DataFrame({"x": [4], "y": ["d"]}), "book.xlsx#A", mode="append")
    assert sheet_rows(workdir / "book.xlsx", "A") == [("x", "y"), (1, "a"), (2, "b"), (4, "d")]
    assert sheet_rows(workdir / "book.xlsx", "B") == [("x", "y"), (3, "c")]
    sheet = openpyxl.load_workbook(workdir / "book.xlsx")["A"]
    assert (sheet.freeze_panes, sheet.auto_filter.ref) == ("A2", "A1:B4")
    assert report.target.mode == "append"


def test_append_with_another_header_is_refused_and_the_book_is_unchanged(workdir: Path) -> None:
    before = (workdir / "book.xlsx").read_bytes()
    with pytest.raises(DataioError) as caught:
        write(pd.DataFrame({"x": [4], "z": ["d"]}), "book.xlsx#A", mode="append")
    assert caught.value.code == "WRITE_FAILED"
    assert "['x', 'y']" in caught.value.message and "['x', 'z']" in caught.value.message
    assert (workdir / "book.xlsx").read_bytes() == before


def test_append_to_a_new_sheet_writes_it(workdir: Path) -> None:
    write(pd.DataFrame({"x": [5]}), "book.xlsx#C", mode="append")
    assert sheet_rows(workdir / "book.xlsx", "C") == [("x",), (5,)]


# --- info / formats --------------------------------------------------------------


def test_info_json_lists_the_sheets(workdir: Path) -> None:
    code, payload = invoke_json("info", "book.xlsx")
    assert code == 0
    assert payload["parts"] == ["A", "B"]


def test_formats_json_lists_the_excel_formats(workdir: Path) -> None:
    code, payload = invoke_json("formats")
    assert code == 0
    listed = {entry["name"]: (entry["read"], entry["write"], entry["append"]) for entry in payload["formats"]}
    assert listed["xlsx"] == (True, True, True)
    assert listed["xls"] == listed["xlsb"] == listed["ods"] == (True, False, False)
