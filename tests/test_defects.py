"""Small defects after E-002..E-005 (DATAIO-022): one test per defect, through the public API and the CLI under --json."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import httpx
import openpyxl
import pandas as pd
import pytest
from typer.testing import CliRunner

from rb_dataio import DataioError, convert, read, write
from rb_dataio.cli import app
from rb_dataio.core.errors import ProviderError
from rb_dataio.formats.http import WebProvider

runner = CliRunner()


@pytest.fixture
def folder(tmp_path: Path, data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def invoke_json(*args: str) -> tuple[int, dict]:
    result = runner.invoke(app, [*args, "--json"])
    return result.exit_code, json.loads(result.stdout.splitlines()[0])


def test_an_int_column_stays_int_when_parts_are_stacked(folder: Path) -> None:
    book = openpyxl.Workbook()
    book.active.title = "A"
    book["A"].append(["id", "n"])
    book["A"].append([1, 30])
    book.create_sheet("B").append(["id", "other"])
    book["B"].append([2, "x"])
    book.save("book.xlsx")
    stacked = read("book.xlsx#*")
    assert str(stacked["n"].iloc[0]) == "30"
    assert stacked["n"].tolist()[0] == 30
    assert pd.isna(stacked["n"].iloc[1])


def test_an_int_column_stays_int_when_files_are_merged(folder: Path) -> None:
    Path("in").mkdir()
    Path("in/a.csv").write_text("id,n\n1,30\n", encoding="utf-8")
    Path("in/b.csv").write_text("id,other\n2,x\n", encoding="utf-8")
    merged = read("in/*.csv")
    assert str(merged["n"].iloc[0]) == "30"
    assert pd.isna(merged["n"].iloc[1])


def test_a_failed_append_does_not_send_the_caller_to_the_folder(folder: Path) -> None:
    Path("t.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(DataioError) as caught:
        write(pd.DataFrame({"x": [1]}), "t.csv", mode="append")
    assert caught.value.code == "WRITE_FAILED"
    assert "folder" not in (caught.value.action or "")


def test_an_sql_error_points_at_the_sql(folder: Path) -> None:
    Path("t.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(DataioError) as caught:
        read("t.csv", query="SELECT nope FROM data")
    assert caught.value.code == "READ_FAILED"
    action = caught.value.action or ""
    assert "SQL" in action
    assert "encoding" not in action
    assert "sep" not in action


def test_a_text_that_starts_with_equals_is_a_string_in_xlsx(folder: Path) -> None:
    write(pd.DataFrame({"t": ["=1+1"]}), "x.xlsx")
    cell = openpyxl.load_workbook("x.xlsx").active["A2"]
    assert (cell.data_type, cell.value) == ("s", "=1+1")
    assert read("x.xlsx")["t"].tolist() == ["=1+1"]


def test_mode_error_looks_at_the_part_in_a_sqlite_base(folder: Path) -> None:
    write(pd.DataFrame({"a": [1]}), "x.sqlite#t1")
    write(pd.DataFrame({"a": [2]}), "x.sqlite#t2", mode="error")
    assert read("x.sqlite#t2")["a"].tolist() == [2]
    with pytest.raises(DataioError) as caught:
        write(pd.DataFrame({"a": [3]}), "x.sqlite#t1", mode="error")
    assert caught.value.code == "TARGET_EXISTS"
    with sqlite3.connect("x.sqlite") as connection:
        assert connection.execute("SELECT a FROM t1").fetchall() == [(1,)]


def test_mode_error_looks_at_the_part_in_an_xlsx_book(folder: Path) -> None:
    write(pd.DataFrame({"a": [1]}), "book.xlsx#Sheet1")
    write(pd.DataFrame({"a": [2]}), "book.xlsx#Sheet2", mode="error")
    assert read("book.xlsx#Sheet2")["a"].tolist() == [2]
    with pytest.raises(DataioError) as caught:
        write(pd.DataFrame({"a": [3]}), "book.xlsx#Sheet1", mode="error")
    assert caught.value.code == "TARGET_EXISTS"


def test_an_http_404_has_the_status_and_the_url_and_no_body(monkeypatch: pytest.MonkeyPatch) -> None:
    url = "https://example.com/missing.csv"
    handler = lambda request: httpx.Response(404, text="<html>SECRET PAGE BODY</html>")  # noqa: E731
    monkeypatch.setattr(WebProvider, "transport", httpx.MockTransport(handler))
    with pytest.raises(ProviderError) as caught:
        read(url)
    error = caught.value
    assert error.code == "PROVIDER_ERROR"
    assert error.status == 404
    assert url in error.message
    assert "404" in error.message
    assert "SECRET" not in error.message
    assert "retry" not in (error.action or "").lower()


def test_the_cli_names_its_flags_for_a_schema_mismatch(folder: Path) -> None:
    Path("in").mkdir()
    Path("in/a.csv").write_text("a\n1\n", encoding="utf-8")
    Path("in/b.csv").write_text("b\n2\n", encoding="utf-8")
    code, payload = invoke_json("convert", "in/*.csv", "out.csv", "--strict")
    assert code == 2
    assert payload["error"]["code"] == "SCHEMA_MISMATCH"
    assert "--strict" in payload["error"]["action"]
    assert "strict=" not in payload["error"]["action"]
    with pytest.raises(DataioError) as caught:
        convert("in/*.csv", "out.csv", strict=True)
    assert "strict=False" in (caught.value.action or "")


def test_the_cli_names_its_flags_for_a_target_that_exists(folder: Path) -> None:
    Path("a.csv").write_text("a\n1\n", encoding="utf-8")
    Path("b.csv").write_text("a\n2\n", encoding="utf-8")
    code, payload = invoke_json("convert", "a.csv", "b.csv", "--mode", "error")
    assert code == 1
    assert payload["error"]["code"] == "TARGET_EXISTS"
    assert "--mode replace" in payload["error"]["action"]
    assert "mode=" not in payload["error"]["action"]
    with pytest.raises(DataioError) as caught:
        convert("a.csv", "b.csv", mode="error")
    assert "mode='replace'" in (caught.value.action or "")


def test_a_batch_report_has_the_warnings_of_the_reads_prefixed_by_the_file(folder: Path) -> None:
    Path("in").mkdir()
    Path("in/a.csv").write_text("x,,x\n1,2,3\n", encoding="utf-8")  # a header with an empty and a repeated name
    Path("in/b.csv").write_text("x,y\n1,2\n", encoding="utf-8")
    report = convert("in/*.csv", "out/{stem}.csv")
    assert len(report.warnings) == 1
    assert report.warnings[0].startswith("in/a.csv: ")


def test_two_sources_with_one_stem_are_refused_before_anything_is_written(folder: Path) -> None:
    for name in ("a", "b"):
        Path(name).mkdir()
        Path(name, "x.csv").write_text("v\n1\n", encoding="utf-8")
    with pytest.raises(DataioError) as caught:
        convert("**/x.csv", "out/{stem}.csv")
    assert caught.value.code == "INVALID_ARGUMENTS"
    assert "a/x.csv" in caught.value.message
    assert "b/x.csv" in caught.value.message
    assert not Path("out").exists()


@pytest.mark.parametrize("options", [{"split_by": "a"}, {"chunk_rows": 1}])
def test_a_split_needs_a_placeholder_in_the_target(folder: Path, options: dict) -> None:
    with pytest.raises(DataioError) as caught:
        write(pd.DataFrame({"a": [1, 2]}), "out.csv", **options)
    assert caught.value.code == "INVALID_ARGUMENTS"
    assert "{column}" in caught.value.message
    assert "{n}" in caught.value.message
    assert not Path("out.csv").exists()
