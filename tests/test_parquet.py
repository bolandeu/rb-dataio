"""Parquet through the public library API and the CLI under --json, on files the tests write."""

from __future__ import annotations

import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from rb_dataio import DataioError, read, write
from rb_dataio.cli import app

runner = CliRunner()


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def typed_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": pd.array([1, 2, None], dtype="Int64"),
            "price": [1.5, None, 3.25],
            "phrase": ["купить ёлку", "ёлка цена", None],
            "flag": pd.array([True, False, None], dtype="boolean"),
            "day": pd.to_datetime(["2024-12-01", "2024-12-02", None]),
        }
    )


def test_typed_frame_round_trips(workdir: Path) -> None:
    write(typed_frame(), "a.parquet")
    back = read("a.parquet")
    assert back.columns.tolist() == ["id", "price", "phrase", "flag", "day"]
    assert back["id"].tolist() == [1, 2, pd.NA]
    assert back["price"].tolist()[0::2] == [1.5, 3.25] and pd.isna(back["price"][1])
    assert back["phrase"].tolist()[:2] == ["купить ёлку", "ёлка цена"] and pd.isna(back["phrase"][2])
    assert back["flag"].tolist() == [True, False, pd.NA]
    assert back["day"].tolist()[:2] == [pd.Timestamp("2024-12-01"), pd.Timestamp("2024-12-02")]
    assert pd.isna(back["day"][2])
    assert [str(dtype) for dtype in back.dtypes] == ["Int64", "float64", "str", "boolean", "datetime64[us]"]


def test_date_and_timestamp_columns_keep_their_type(workdir: Path) -> None:
    frame = pd.DataFrame({"d": [pd.Timestamp("2024-12-01").date()], "t": [pd.Timestamp("2024-12-01 10:30:15")]})
    write(frame, "a.parquet")
    back = read("a.parquet")
    assert back["d"].tolist() == [pd.Timestamp("2024-12-01")]
    assert back["t"].tolist() == [pd.Timestamp("2024-12-01 10:30:15")]


def test_string_with_leading_zero_stays_a_string(workdir: Path) -> None:
    write(pd.DataFrame({"code": ["007", "010"]}), "a.parquet")
    assert read("a.parquet")["code"].tolist() == ["007", "010"]


def test_numeric_looking_string_stays_a_string(workdir: Path) -> None:
    write(pd.DataFrame({"code": ["12", "34"]}), "a.parquet")
    assert read("a.parquet")["code"].tolist() == ["12", "34"]


def test_pyarrow_is_neither_a_dependency_nor_imported() -> None:
    requires = importlib.metadata.requires("rb-dataio") or []
    assert not [line for line in requires if line.lower().startswith("pyarrow")]
    assert "duckdb" in " ".join(requires)
    code = "import sys, rb_dataio; rb_dataio.read('a\\nb', format='csv'); print('pyarrow' in sys.modules)"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)  # noqa: S603
    assert result.stdout.strip() == "False"


def test_convert_csv_to_parquet_and_back(workdir: Path) -> None:
    (workdir / "a.csv").write_text("phrase,freq\nкупить ёлку,10\nёлка цена,7\n", encoding="utf-8")
    for source, target in [("a.csv", "a.parquet"), ("a.parquet", "b.csv")]:
        result = runner.invoke(app, ["convert", source, target, "--json"])
        assert result.exit_code == 0, result.stdout
        assert json.loads(result.stdout)["ok"] is True
    assert read("b.csv").to_dict("list") == {"phrase": ["купить ёлку", "ёлка цена"], "freq": [10, 7]}


def test_formats_lists_parquet_without_append() -> None:
    result = runner.invoke(app, ["formats", "--json"])
    entry = next(item for item in json.loads(result.stdout)["formats"] if item["name"] == "parquet")
    assert (entry["extensions"], entry["read"], entry["write"], entry["append"]) == ([".parquet"], True, True, False)


def test_append_is_format_unsupported_and_the_file_is_unchanged(workdir: Path) -> None:
    write(pd.DataFrame({"a": [1]}), "a.parquet")
    before = (workdir / "a.parquet").read_bytes()
    with pytest.raises(DataioError) as caught:
        write(pd.DataFrame({"a": [2]}), "a.parquet", mode="append")
    assert (caught.value.code, caught.value.exit_code) == ("FORMAT_UNSUPPORTED", 2)
    assert (workdir / "a.parquet").read_bytes() == before
