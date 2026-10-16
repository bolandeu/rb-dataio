"""The core frame through the public library API: read, write, convert, info, formats, the address and the errors.

Real temporary files; every CSV is written by the test itself.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pandas as pd
import pytest

from rb_dataio import DataioError, convert, formats, info, read, write
from rb_dataio.core.dataio import address

# The package root's `formats` is the function; the formats package is reached through importlib.
format_modules = importlib.import_module("rb_dataio.formats")
csv_module = importlib.import_module("rb_dataio.formats.csv")

PHRASES = "phrase,freq\nкупить ёлку,10\nёлка цена,7\nискусственная ёлка,3\n"
FORMATS_FIXTURE = Path(__file__).parent / "data" / "frame" / "formats"


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A folder with a.csv (phrase,freq; 3 rows), the current directory, so addresses stay short."""
    (tmp_path / "a.csv").write_text(PHRASES, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


# --- read / write / convert ------------------------------------------------------


def test_read_returns_the_table(workdir: Path) -> None:
    frame = read("a.csv")
    assert list(frame.columns) == ["phrase", "freq"]
    assert frame["phrase"].tolist() == ["купить ёлку", "ёлка цена", "искусственная ёлка"]
    assert frame["freq"].tolist() == [10, 7, 3]


def test_write_keeps_the_content_and_reports_the_target(workdir: Path) -> None:
    report = write(read("a.csv"), "b.csv")
    assert (workdir / "b.csv").read_text(encoding="utf-8") == PHRASES
    assert report.to_dict() == {
        "target": {"uri": "b.csv", "format": "csv", "mode": "replace", "rows": 3, "columns": ["phrase", "freq"]},
        "warnings": [],
    }


def test_convert_reports_the_source_and_the_target(workdir: Path) -> None:
    report = convert("a.csv", "b.csv").to_dict()
    assert report["source"] == {
        "uri": "a.csv",
        "format": "csv",
        "encoding": "utf-8",
        "delimiter": ",",
        "rows": 3,
        "columns": ["phrase", "freq"],
    }
    assert report["target"]["rows"] == 3
    assert (workdir / "b.csv").read_text(encoding="utf-8") == PHRASES


def test_explicit_encoding_and_delimiter_are_used(workdir: Path) -> None:
    (workdir / "win.csv").write_bytes("phrase;freq\nёлка;5\n".encode("cp1251"))
    report = convert("win.csv", "out.csv", in_encoding="cp1251", in_sep=";", out_sep="|").to_dict()
    assert (report["source"]["encoding"], report["source"]["delimiter"]) == ("cp1251", ";")
    assert (workdir / "out.csv").read_text(encoding="utf-8") == "phrase|freq\nёлка|5\n"


def test_limit_keeps_the_first_rows(workdir: Path) -> None:
    assert read("a.csv", limit=2)["phrase"].tolist() == ["купить ёлку", "ёлка цена"]


def test_negative_limit_is_invalid(workdir: Path) -> None:
    with pytest.raises(DataioError) as caught:
        read("a.csv", limit=-1)
    assert caught.value.code == "INVALID_ARGUMENTS"


def test_dry_run_reports_and_writes_nothing(workdir: Path) -> None:
    report = convert("a.csv", "b.csv", dry_run=True).to_dict()
    assert report["target"] == {
        "uri": "b.csv",
        "format": "csv",
        "mode": "replace",
        "rows": 3,
        "columns": ["phrase", "freq"],
    }
    assert not (workdir / "b.csv").exists()


def test_format_parameter_wins_over_the_extension(workdir: Path) -> None:
    (workdir / "a.data").write_text(PHRASES, encoding="utf-8")
    assert read("a.data", format="csv").shape == (3, 2)


# --- the address ------------------------------------------------------------------


def test_parameter_wins_over_the_sheet_in_the_address() -> None:
    assert address.parse("book.xlsx#Sheet1").fragment == "Sheet1"
    assert address.parse("book.xlsx#Sheet1", sheet="Other").fragment == "Other"


def test_fragment_of_a_base_is_the_table() -> None:
    parsed = address.parse("data.duckdb#phrases")
    assert (parsed.scheme, parsed.path, parsed.fragment) == ("file", "data.duckdb", "phrases")
    assert address.parse("data.duckdb#phrases", table="other").fragment == "other"


@pytest.mark.parametrize(
    ("text", "scheme", "path"),
    [
        ("-", "stdio", "-"),
        ("gsheet://1AbC", "gsheet", "1AbC"),
        ("https://example.com/a.csv", "https", "example.com/a.csv"),
        ("data/a.csv", "file", "data/a.csv"),
    ],
)
def test_scheme_is_recognised(text: str, scheme: str, path: str) -> None:
    parsed = address.parse(text)
    assert (parsed.scheme, parsed.path, parsed.fragment) == (scheme, path, None)


def test_placeholders_are_parsed() -> None:
    assert address.parse("out/{region}/part_{n}.csv").placeholders == ("region", "n")


@pytest.mark.parametrize("source", ["-", "gsheet://1AbC", "https://example.com/a.csv"])
def test_other_schemes_are_not_supported_yet(source: str) -> None:
    with pytest.raises(DataioError) as caught:
        read(source)
    assert (caught.value.code, caught.value.exit_code) == ("FORMAT_UNSUPPORTED", 2)


# --- errors ---------------------------------------------------------------------


def test_one_line_string_that_is_no_file_is_source_not_found(workdir: Path) -> None:
    with pytest.raises(DataioError) as caught:
        read("phrases.csvv")
    error = caught.value
    assert (error.code, error.exit_code) == ("SOURCE_NOT_FOUND", 2)
    assert "'phrases.csvv'" in error.message
    assert error.action == "Pass format='text' to read the string as text"


def test_unknown_format_parameter_lists_the_known_formats(workdir: Path) -> None:
    with pytest.raises(DataioError) as caught:
        read("a.csv", format="xyz")
    assert caught.value.code == "FORMAT_UNKNOWN"
    assert "csv" in (caught.value.action or "")


def test_unreadable_source_is_read_failed(workdir: Path) -> None:
    (workdir / "bad.csv").write_bytes(b"\x00\x01phrase\xff\xfe")
    with pytest.raises(DataioError) as caught:
        read("bad.csv")
    assert (caught.value.code, caught.value.exit_code) == ("READ_FAILED", 1)
    assert "'bad.csv'" in caught.value.message


def test_target_in_a_missing_folder_is_write_failed(workdir: Path) -> None:
    with pytest.raises(DataioError) as caught:
        convert("a.csv", "missing/b.csv")
    assert (caught.value.code, caught.value.exit_code) == ("WRITE_FAILED", 1)
    assert "'missing/b.csv'" in caught.value.message


def test_mode_error_refuses_an_existing_target(workdir: Path) -> None:
    (workdir / "b.csv").write_text("old\n", encoding="utf-8")
    with pytest.raises(DataioError) as caught:
        convert("a.csv", "b.csv", mode="error")
    assert (caught.value.code, caught.value.exit_code) == ("TARGET_EXISTS", 1)
    assert (workdir / "b.csv").read_text(encoding="utf-8") == "old\n"


def test_append_is_refused_by_a_format_that_cannot_append(workdir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(csv_module.CsvAdapter, "appends", False)
    with pytest.raises(DataioError) as caught:
        convert("a.csv", "b.csv", mode="append")
    assert (caught.value.code, caught.value.exit_code) == ("FORMAT_UNSUPPORTED", 2)


def test_unknown_mode_is_invalid(workdir: Path) -> None:
    with pytest.raises(DataioError) as caught:
        convert("a.csv", "b.csv", mode="merge")
    assert caught.value.code == "INVALID_ARGUMENTS"


# --- info / formats -------------------------------------------------------------


def test_info_describes_the_source(workdir: Path) -> None:
    rows = "".join(f"фраза {n},{n}\n" for n in range(7))
    (workdir / "big.csv").write_text("phrase,freq\n" + rows, encoding="utf-8")
    described = info("big.csv").to_dict()
    assert described["source"]["format"] == "csv"
    assert described["source"]["rows"] == 7
    assert described["types"] == {"phrase": "str", "freq": "int64"}
    assert described["preview"] == [{"phrase": f"фраза {n}", "freq": n} for n in range(5)]


def test_formats_lists_csv_with_its_abilities() -> None:
    [csv] = [entry.to_dict() for entry in formats() if entry.name == "csv"]
    assert csv == {
        "name": "csv",
        "extensions": [".csv"],
        "read": True,
        "write": True,
        "append": True,
        "options": ["encoding", "sep"],
    }


def test_a_new_module_in_the_formats_package_is_a_new_format(monkeypatch: pytest.MonkeyPatch) -> None:
    """tests/data/frame/formats/probe.py joins the formats package: no other edit makes it known."""
    monkeypatch.setattr(format_modules, "__path__", [*format_modules.__path__, str(FORMATS_FIXTURE)])
    [probe] = [entry.to_dict() for entry in formats() if entry.name == "probe"]
    assert probe == {
        "name": "probe",
        "extensions": [".probe"],
        "read": True,
        "write": False,
        "append": False,
        "options": [],
    }


def test_a_format_without_write_refuses_to_write(monkeypatch: pytest.MonkeyPatch, workdir: Path) -> None:
    monkeypatch.setattr(format_modules, "__path__", [*format_modules.__path__, str(FORMATS_FIXTURE)])
    (workdir / "a.probe").write_text("ignored", encoding="utf-8")
    assert read("a.probe").to_dict("list") == {"probe": ["ok"]}
    with pytest.raises(DataioError) as caught:
        write(pd.DataFrame({"x": [1]}), "b.probe")
    assert caught.value.code == "FORMAT_UNSUPPORTED"
