"""query=: SQL over a source, through the public library API and the CLI under --json.

Over a csv or parquet file DuckDB reads the file itself; over any other source the table
read as usual is the table `data`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from rb_dataio import DataioError, info, read, write
from rb_dataio.cli import app
from rb_dataio.core.dataio.api import Source
from rb_dataio.formats.parquet import ParquetAdapter

PHRASES = "phrase,freq\nёлка,5\nель,20\nсосна,11\n"
OVER_TEN = "select phrase from data where freq > 10"
runner = CliRunner()


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, data_dir: Path) -> Path:
    """The current directory with phrases.csv (phrase,freq: 5, 20, 11)."""
    (tmp_path / "phrases.csv").write_text(PHRASES, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def invoke_json(*args: str) -> tuple[int, dict]:
    result = runner.invoke(app, [*args, "--json"])
    lines = result.stdout.splitlines()
    assert len(lines) == 1, f"stdout must be one JSON object; got {result.stdout!r}, stderr {result.stderr!r}"
    return result.exit_code, json.loads(lines[0])


def test_a_query_over_a_csv_returns_the_matching_rows_and_columns(workdir: Path) -> None:
    assert read("phrases.csv", query=OVER_TEN).to_dict("list") == {"phrase": ["ель", "сосна"]}


@pytest.mark.parametrize(
    "source",
    [
        [{"phrase": "ёлка", "freq": 5}, {"phrase": "ель", "freq": 20}, {"phrase": "сосна", "freq": 11}],
        pd.DataFrame({"phrase": ["ёлка", "ель", "сосна"], "freq": [5, 20, 11]}),
    ],
    ids=["records", "dataframe"],
)
def test_a_query_over_a_python_object_runs_over_the_table_data(source: Source) -> None:
    assert read(source, query=OVER_TEN).to_dict("list") == {"phrase": ["ель", "сосна"]}


def test_a_query_over_a_text_runs_over_its_lines() -> None:
    assert read("ёлка\nель\n", query="select text from data where text like 'ел%'").to_dict("list") == {"text": ["ель"]}


def test_duckdb_reads_a_csv_itself_and_gives_the_result_of_the_read_table(workdir: Path, reads: list[Path]) -> None:
    direct = read("phrases.csv", query="select * from data where freq > 10 order by freq")
    assert reads == []
    over_table = read(read("phrases.csv"), query="select * from data where freq > 10 order by freq")
    pd.testing.assert_frame_equal(direct, over_table)
    assert direct.to_dict("list") == {"phrase": ["сосна", "ель"], "freq": [11, 20]}


def test_duckdb_reads_a_parquet_itself_and_gives_the_result_of_the_read_table(
    workdir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write(pd.DataFrame({"phrase": ["ёлка", "ель", "сосна"], "freq": [5, 20, 11]}), "phrases.parquet")
    over_table = read(read("phrases.parquet"), query=OVER_TEN)

    def refuse(*_: object) -> None:
        raise AssertionError("the parquet adapter read the file")

    monkeypatch.setattr(ParquetAdapter, "read", refuse)
    direct = read("phrases.parquet", query=OVER_TEN)
    pd.testing.assert_frame_equal(direct, over_table)
    assert direct.to_dict("list") == {"phrase": ["ель", "сосна"]}


def test_a_query_over_a_cp1251_csv_with_semicolons_still_works(workdir: Path) -> None:
    (workdir / "win.csv").write_bytes("phrase;freq\nёлка;5\nель;20\n".encode("cp1251"))
    assert read("win.csv", query=OVER_TEN).to_dict("list") == {"phrase": ["ель"]}


def test_a_sql_error_is_read_failed_with_the_duckdb_message(workdir: Path) -> None:
    with pytest.raises(DataioError) as caught:
        read("phrases.csv", query="select nope from data")
    assert (caught.value.code, caught.value.exit_code) == ("READ_FAILED", 1)
    assert 'Referenced column "nope" not found' in caught.value.message


def test_a_sql_error_over_an_object_is_read_failed() -> None:
    with pytest.raises(DataioError) as caught:
        read([{"a": 1}], query="select nope from data")
    assert caught.value.code == "READ_FAILED"
    assert 'Referenced column "nope" not found' in caught.value.message


def test_info_describes_the_result_of_the_query(workdir: Path) -> None:
    described = info("phrases.csv", query="select phrase, freq from data where freq > 10")
    assert (described.source.rows, described.source.columns) == (2, ["phrase", "freq"])
    assert described.preview == [{"phrase": "ель", "freq": 20}, {"phrase": "сосна", "freq": 11}]


def test_cli_convert_query_writes_the_result(workdir: Path) -> None:
    code, payload = invoke_json("convert", "phrases.csv", "out.csv", "--query", OVER_TEN)
    assert code == 0
    assert (payload["source"]["rows"], payload["source"]["columns"]) == (2, ["phrase"])
    assert (workdir / "out.csv").read_text(encoding="utf-8") == "phrase\nель\nсосна\n"


def test_cli_info_query_and_its_sql_error(workdir: Path) -> None:
    code, payload = invoke_json("info", "phrases.csv", "--query", OVER_TEN)
    assert code == 0
    assert payload["source"]["rows"] == 2
    code, payload = invoke_json("info", "phrases.csv", "--query", "select nope from data")
    assert code == 1
    assert payload["error"]["code"] == "READ_FAILED"
