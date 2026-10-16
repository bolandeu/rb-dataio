"""Python objects through the public library API: in-memory sources for read(), in-memory results of write()."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from rb_dataio import DataioError, read, write

PHRASES = pd.DataFrame({"phrase": ["купить ёлку", "ёлка цена"], "freq": [10, 7]})


# --- read: objects in, a table out -----------------------------------------------


@pytest.mark.parametrize("source", [["a", "b"], "a\nb", "a\n\nb\n"], ids=["list", "text", "blank lines"])
def test_strings_become_one_column_text(source: str | list[str]) -> None:
    assert read(source).to_dict("list") == {"text": ["a", "b"]}


def test_strings_that_look_like_numbers_stay_text() -> None:
    assert read(["007", "12"]).to_dict("list") == {"text": ["007", "12"]}


def test_list_of_dicts_becomes_columns() -> None:
    assert read([{"a": 1, "b": 2}]).to_dict("list") == {"a": [1], "b": [2]}


def test_dict_of_lists_becomes_columns() -> None:
    assert read({"a": [1, 2], "b": [3, 4]}).to_dict("list") == {"a": [1, 2], "b": [3, 4]}


def test_dict_of_values_becomes_key_and_value() -> None:
    assert read({"x": 1, "y": 2}).to_dict("list") == {"key": ["x", "y"], "value": [1, 2]}


def test_named_series_keeps_its_name() -> None:
    assert read(pd.Series([3, 5], name="freq")).to_dict("list") == {"freq": [3, 5]}


def test_unnamed_series_is_column_value() -> None:
    assert read(pd.Series([3, 5])).to_dict("list") == {"value": [3, 5]}


def test_dataframe_comes_back_as_it_is() -> None:
    assert read(PHRASES).to_dict("list") == {"phrase": ["купить ёлку", "ёлка цена"], "freq": [10, 7]}


def test_format_text_reads_a_one_line_string_as_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert read("ёлка", format="text").to_dict("list") == {"text": ["ёлка"]}


def test_object_that_is_no_table_is_invalid() -> None:
    with pytest.raises(DataioError) as caught:
        read(42)  # ty: ignore[invalid-argument-type]
    assert caught.value.code == "INVALID_ARGUMENTS"


# --- write: a table in, an object out ---------------------------------------------


def test_records_are_returned_and_nothing_is_written(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert write(PHRASES, format="records") == [
        {"phrase": "купить ёлку", "freq": 10},
        {"phrase": "ёлка цена", "freq": 7},
    ]
    assert list(tmp_path.iterdir()) == []


def test_no_target_and_no_format_returns_records() -> None:
    assert write(PHRASES) == [{"phrase": "купить ёлку", "freq": 10}, {"phrase": "ёлка цена", "freq": 7}]


def test_missing_value_is_none_in_records() -> None:
    assert write(pd.DataFrame({"freq": [1.5, None]}), format="records") == [{"freq": 1.5}, {"freq": None}]


def test_list_is_the_first_column() -> None:
    assert write(PHRASES, format="list") == ["купить ёлку", "ёлка цена"]


def test_dict_is_columns_of_values() -> None:
    assert write(PHRASES, format="dict") == {"phrase": ["купить ёлку", "ёлка цена"], "freq": [10, 7]}


def test_text_is_one_value_per_line() -> None:
    assert write(PHRASES[["phrase"]], format="text") == "купить ёлку\nёлка цена\n"


def test_csv_is_csv_text() -> None:
    assert write(PHRASES, format="csv") == "phrase,freq\nкупить ёлку,10\nёлка цена,7\n"


def test_json_is_json_text() -> None:
    assert json.loads(write(PHRASES, format="json")) == [
        {"phrase": "купить ёлку", "freq": 10},
        {"phrase": "ёлка цена", "freq": 7},
    ]


def test_objects_round_trip() -> None:
    assert read(write(PHRASES, format="records")).equals(PHRASES)
    assert read(write(PHRASES, format="dict")).equals(PHRASES)


def test_unknown_in_memory_format_lists_the_known_ones() -> None:
    with pytest.raises(DataioError) as caught:
        write(PHRASES, format="xyz")
    assert caught.value.code == "FORMAT_UNKNOWN"
    assert "records" in (caught.value.action or "")
