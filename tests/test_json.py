"""JSON and jsonl through the public library API: the shapes of a read, nested objects, the written file, errors.

Fixtures: tests/data/json/ (records, columns, jsonl of the same table; a nested record).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
import pytest

from rb_dataio import DataioError, read, write

FIXTURES = Path(__file__).parent / "data" / "json"
PHRASES = {"phrase": ["купить ёлку", "ёлка цена"], "freq": [10, 7], "day": ["2024-12-01", "2024-12-02"]}


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, data_dir: Path) -> Path:
    shutil.copytree(FIXTURES, tmp_path, dirs_exist_ok=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


# --- read -------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["records.json", "columns.json", "records.jsonl"])
def test_every_shape_reads_the_same_table(workdir: Path, name: str) -> None:
    frame = read(name)
    assert frame.drop(columns="day").to_dict("list") == {"phrase": PHRASES["phrase"], "freq": PHRASES["freq"]}
    assert frame["day"].tolist() == [pd.Timestamp("2024-12-01"), pd.Timestamp("2024-12-02")]


def test_nested_object_becomes_dotted_columns_and_a_list_json_text(workdir: Path) -> None:
    frame = read("nested.json")
    assert frame.to_dict("list") == {"user.name": ["Иван"], "tags": ['["a", "b"]']}


def test_broken_json_is_read_failed_with_the_address_and_the_line(workdir: Path) -> None:
    (workdir / "broken.json").write_text('[\n  {"phrase": "ёлка"},\n  {"phrase" "пихта"}\n]\n', encoding="utf-8")
    with pytest.raises(DataioError) as caught:
        read("broken.json")
    assert (caught.value.code, caught.value.exit_code) == ("READ_FAILED", 1)
    assert "'broken.json'" in caught.value.message
    assert "line 3" in caught.value.message


def test_broken_jsonl_names_the_line(workdir: Path) -> None:
    (workdir / "broken.jsonl").write_text('{"phrase": "ёлка"}\n{"phrase": \n', encoding="utf-8")
    with pytest.raises(DataioError) as caught:
        read("broken.jsonl")
    assert caught.value.code == "READ_FAILED"
    assert "'broken.jsonl'" in caught.value.message
    assert "line 2" in caught.value.message


# --- write ------------------------------------------------------------------------


def test_json_is_records_with_indent_cyrillic_and_iso_dates(workdir: Path) -> None:
    frame = pd.DataFrame({"phrase": ["ёлка"], "day": [pd.Timestamp("2024-12-01")]})
    write(frame, "out.json")
    text = (workdir / "out.json").read_text(encoding="utf-8")
    assert text == '[\n  {\n    "phrase": "ёлка",\n    "day": "2024-12-01T00:00:00"\n  }\n]\n'


def test_jsonl_is_one_record_per_line(workdir: Path) -> None:
    write(pd.DataFrame({"phrase": ["ёлка", "пихта"], "freq": [3, None]}), "out.jsonl")
    lines = (workdir / "out.jsonl").read_text(encoding="utf-8").splitlines()
    assert lines == ['{"phrase": "ёлка", "freq": 3.0}', '{"phrase": "пихта", "freq": null}']


def test_written_json_reads_back(workdir: Path) -> None:
    for name in ("back.json", "back.jsonl"):
        write(read("records.json"), name)
        assert read(name).equals(read("records.json"))


# --- whole numbers with a missing value ---------------------------------------------


def test_jsonl_int_column_with_null_is_int64(workdir: Path) -> None:
    Path("n.jsonl").write_text('{"phrase":"a","freq":5}\n{"phrase":"b","freq":null}\n', encoding="utf-8")
    frame = read("n.jsonl")
    assert str(frame["freq"].dtype) == "Int64"
    assert frame["freq"].tolist()[0] == 5
    assert frame["freq"].isna().tolist() == [False, True]


def test_json_int_column_with_null_is_int64(workdir: Path) -> None:
    Path("n.json").write_text('[{"phrase":"a","freq":5},{"phrase":"b","freq":null}]', encoding="utf-8")
    assert str(read("n.json")["freq"].dtype) == "Int64"


def test_jsonl_float_column_with_null_stays_float64(workdir: Path) -> None:
    Path("f.jsonl").write_text('{"x":1.5}\n{"x":null}\n', encoding="utf-8")
    assert str(read("f.jsonl")["x"].dtype) == "float64"
