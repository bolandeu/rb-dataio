"""join(): the main source with the lookups' columns, matched by the named key columns (seam: the library)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from rb_dataio import DataioError, join, read, restore, write
from rb_dataio.core.errors import WriteOverSource

MAIN = [{"sku": 1, "name": "a"}, {"sku": 2, "name": "b"}, {"sku": 3, "name": "c"}]
PRICES = [{"sku": 2, "price": 20}, {"sku": 1, "price": 10}]


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, data_dir: Path) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _rows(address: str) -> list[dict[str, Any]]:
    """The target read back, as records (an empty cell is None)."""
    return write(read(address))


def _keys(address: str, column: str = "sku") -> list[Any]:
    return [row[column] for row in _rows(address)]


def test_left_join_by_default_keeps_main_order_and_counts_matches(workdir: Path) -> None:
    report = join(MAIN, "out.csv", lookups=[PRICES], on=["sku"])

    assert _rows("out.csv") == [
        {"sku": 1, "name": "a", "price": 10},
        {"sku": 2, "name": "b", "price": 20},
        {"sku": 3, "name": "c", "price": None},
    ]
    assert report.to_dict()["lookups"] == [{"uri": "<list>", "rows": 2, "matched": 2, "unmatched": 1, "empty_keys": 0}]
    assert report.to_dict()["source"]["rows"] == 3


def test_several_keys_match_only_when_all_are_equal(workdir: Path) -> None:
    main = [{"phrase": "купить", "region": 213}, {"phrase": "купить", "region": 2}]
    lookup = [{"phrase": "купить", "region": 2, "shows": 50}]

    join(main, "out.csv", lookups=[lookup], on=["phrase", "region"])

    assert _rows("out.csv") == [
        {"phrase": "купить", "region": 213, "shows": None},
        {"phrase": "купить", "region": 2, "shows": 50},
    ]


def test_key_named_on_each_side_keeps_the_main_name_only(workdir: Path) -> None:
    lookup = [{"article": 1, "price": 10}]

    report = join(MAIN, "out.csv", lookups=[lookup], on=["sku=article"])

    assert report.to_dict()["target"]["columns"] == ["sku", "name", "price"]
    assert _keys("out.csv", "price") == [10, None, None]


@pytest.mark.parametrize("on", [[], None])
def test_no_keys_is_invalid_and_writes_nothing(workdir: Path, on: list[str] | None) -> None:
    with pytest.raises(DataioError) as caught:
        join(MAIN, "out.csv", lookups=[PRICES], on=on)

    assert (caught.value.code, caught.value.exit_code) == ("INVALID_ARGUMENTS", 2)
    assert not (workdir / "out.csv").exists()


def test_key_missing_in_the_main_source_names_it_and_its_columns(workdir: Path) -> None:
    write(pd.DataFrame(MAIN), "main.csv")

    with pytest.raises(DataioError) as caught:
        join("main.csv", "out.csv", lookups=[PRICES], on=["article"])

    assert caught.value.code == "INVALID_ARGUMENTS"
    message = caught.value.message
    assert "'main.csv'" in message
    assert "'article'" in message
    assert "sku, name" in message
    assert not (workdir / "out.csv").exists()


def test_key_missing_in_a_lookup_names_it_and_its_columns(workdir: Path) -> None:
    write(pd.DataFrame([{"article": 1, "price": 10}]), "prices.xlsx", sheet="Prices")

    with pytest.raises(DataioError) as caught:
        join(MAIN, "out.csv", lookups=["prices.xlsx#Prices"], on=["sku"])

    assert caught.value.code == "INVALID_ARGUMENTS"
    message = caught.value.message
    assert "'prices.xlsx#Prices'" in message
    assert "'sku'" in message
    assert "article, price" in message
    assert not (workdir / "out.csv").exists()


@pytest.mark.parametrize(
    ("how", "keys"),
    [("left", [1, 2]), ("inner", [2]), ("right", [2, 3]), ("full", [1, 2, 3])],
)
def test_join_kinds(workdir: Path, how: str, keys: list[int]) -> None:
    main = [{"sku": 1, "name": "a"}, {"sku": 2, "name": "b"}]
    lookup = [{"sku": 2, "price": 20}, {"sku": 3, "price": 30}]

    join(main, "out.csv", lookups=[lookup], on=["sku"], how=how)

    assert sorted(_keys("out.csv")) == keys


def test_full_join_takes_the_key_from_the_side_that_has_it(workdir: Path) -> None:
    main = [{"sku": 1, "name": "a"}, {"sku": 2, "name": "b"}]
    lookup = [{"sku": 2, "price": 20}, {"sku": 3, "price": 30}]

    join(main, "out.csv", lookups=[lookup], on=["sku"], how="full")

    assert _rows("out.csv") == [
        {"sku": 1, "name": "a", "price": None},
        {"sku": 2, "name": "b", "price": 20},
        {"sku": 3, "name": None, "price": 30},
    ]


def test_unknown_kind_is_invalid(workdir: Path) -> None:
    with pytest.raises(DataioError) as caught:
        join(MAIN, "out.csv", lookups=[PRICES], on=["sku"], how="outer")

    assert caught.value.code == "INVALID_ARGUMENTS"
    assert not (workdir / "out.csv").exists()


@pytest.mark.parametrize(
    ("how", "rows"),
    [
        ("left", [(1, 10, None), (2, 20, "x"), (3, None, None)]),
        ("inner", [(2, 20, "x")]),
        ("full", [(1, 10, None), (2, 20, "x"), (3, None, None), (5, None, "y")]),
    ],
)
def test_two_lookups_join_in_order(workdir: Path, how: str, rows: list[tuple[Any, ...]]) -> None:
    notes = [{"sku": 2, "note": "x"}, {"sku": 5, "note": "y"}]

    report = join(MAIN, "out.csv", lookups=[PRICES, notes], on=["sku"], how=how)

    assert [(row["sku"], row["price"], row["note"]) for row in _rows("out.csv")] == rows
    assert [entry["rows"] for entry in report.to_dict()["lookups"]] == [2, 2]


def test_right_join_with_two_lookups_is_invalid(workdir: Path) -> None:
    with pytest.raises(DataioError) as caught:
        join(MAIN, "out.csv", lookups=[PRICES, PRICES], on=["sku"], how="right")

    assert caught.value.code == "INVALID_ARGUMENTS"
    assert not (workdir / "out.csv").exists()


def test_keys_compare_as_text_with_outer_spaces_trimmed(workdir: Path) -> None:
    main = pd.DataFrame({"sku": [123, 124]})
    lookup = pd.DataFrame({"sku": ["123", " 124 "], "price": [1, 2]})

    report = join(main, "out.csv", lookups=[lookup], on=["sku"])

    assert _rows("out.csv") == [{"sku": 123, "price": 1}, {"sku": 124, "price": 2}]
    assert report.to_dict()["lookups"][0]["matched"] == 2


@pytest.mark.parametrize(("main_key", "lookup_key"), [("A", "a"), ("Ёлка", "Елка")])
def test_keys_keep_case_and_yo(workdir: Path, main_key: str, lookup_key: str) -> None:
    report = join([{"k": main_key}], "out.csv", lookups=[[{"k": lookup_key, "v": 1}]], on=["k"])

    assert report.to_dict()["lookups"][0]["matched"] == 0


def test_key_column_stays_int(workdir: Path) -> None:
    main = pd.DataFrame({"sku": [123]})
    lookup = pd.DataFrame({"sku": ["123"], "price": [1]})

    join(main, "out.jsonl", lookups=[lookup], on=["sku"])

    assert json.loads((workdir / "out.jsonl").read_text()) == {"sku": 123, "price": 1}


def test_empty_main_key_keeps_the_row_and_matches_nothing(workdir: Path) -> None:
    main = [{"sku": 1, "name": "a"}, {"sku": None, "name": "b"}]
    lookup = [{"sku": 1, "price": 10}, {"sku": None, "price": 99}]

    report = join(main, "out.csv", lookups=[lookup], on=["sku"])

    assert _rows("out.csv") == [
        {"sku": 1, "name": "a", "price": 10},
        {"sku": None, "name": "b", "price": None},
    ]
    assert report.to_dict()["lookups"][0] == {
        "uri": "<list>",
        "rows": 2,
        "matched": 1,
        "unmatched": 1,
        "empty_keys": 1,
    }


def test_repeated_lookup_key_repeats_the_main_row_and_warns(workdir: Path) -> None:
    lookup = [{"sku": 2, "price": 20}, {"sku": 2, "price": 21}]

    report = join(MAIN, "out.csv", lookups=[lookup], on=["sku"])

    assert [(row["sku"], row["price"]) for row in _rows("out.csv")] == [(1, None), (2, 20), (2, 21), (3, None)]
    [warning] = report.warnings
    assert "repeated keys: 2;" in warning
    assert "1 rows added" in warning


def test_repeated_keys_warning_does_not_name_a_key_of_an_unmatched_main_row(workdir: Path) -> None:
    lookup = [{"sku": 1, "price": 10}, {"sku": 1, "price": 11}, {"sku": 3, "price": 30}]

    report = join([{"sku": 1}, {"sku": 2}, {"sku": 3}], "out.csv", lookups=[lookup], on=["sku"], how="left")

    [warning] = report.warnings
    assert "repeated keys: 1;" in warning
    assert "1 rows added" in warning


def test_repeated_keys_warning_of_a_full_join_does_not_name_a_lookup_only_key(workdir: Path) -> None:
    lookup = [{"sku": 2, "price": 20}, {"sku": 2, "price": 21}, {"sku": 5, "price": 50}]

    report = join([{"sku": 1}, {"sku": 2}], "out.csv", lookups=[lookup], on=["sku"], how="full")

    [warning] = report.warnings
    assert "repeated keys: 2;" in warning
    assert "1 rows added" in warning


@pytest.mark.parametrize("how", ["left", "right", "inner", "full"])
def test_no_repeated_lookup_key_means_no_warning(workdir: Path, how: str) -> None:
    lookup = [{"sku": 1, "price": 10}, {"sku": 3, "price": 30}]

    report = join([{"sku": 1}, {"sku": 2}, {"sku": 3}], "out.csv", lookups=[lookup], on=["sku"], how=how)

    assert report.warnings == []


def test_repeated_keys_warning_names_the_first_five(workdir: Path) -> None:
    keys = list(range(1, 8))
    lookup = [{"sku": key, "price": copy} for key in keys for copy in (1, 2)]

    report = join([{"sku": key} for key in keys], "out.csv", lookups=[lookup], on=["sku"])

    [warning] = report.warnings
    assert "repeated keys: 1, 2, 3, 4, 5 and 2 more;" in warning
    assert "7 rows added" in warning


def test_same_named_column_gets_the_part_of_the_lookup_address(workdir: Path) -> None:
    write(pd.DataFrame([{"sku": 1, "name": "x"}]), "prices.xlsx", sheet="Prices")

    report = join(MAIN, "out.csv", lookups=["prices.xlsx#Prices"], on=["sku"])

    assert report.to_dict()["target"]["columns"] == ["sku", "name", "name_Prices"]


def test_same_named_column_gets_the_file_stem_of_a_lookup_with_no_part(workdir: Path) -> None:
    write(pd.DataFrame([{"sku": 1, "name": "x"}]), "prices.csv")

    report = join(MAIN, "out.csv", lookups=["prices.csv"], on=["sku"])

    assert report.to_dict()["target"]["columns"] == ["sku", "name", "name_prices"]


def test_same_named_columns_of_objects_and_a_suffix_taken_twice(workdir: Path) -> None:
    write(pd.DataFrame([{"sku": 1, "name": "x"}]), "one.xlsx", sheet="Prices")
    write(pd.DataFrame([{"sku": 1, "name": "y"}]), "two.xlsx", sheet="Prices")
    lookup = [{"sku": 1, "name": "z"}]

    report = join(MAIN, "out.csv", lookups=["one.xlsx#Prices", "two.xlsx#Prices", lookup], on=["sku"])

    assert report.to_dict()["target"]["columns"] == ["sku", "name", "name_Prices", "name_Prices_2", "name_lookup3"]


def test_columns_and_rename_shape_the_join(workdir: Path) -> None:
    lookup = [{"sku": 1, "name": "x"}]

    report = join(MAIN, "out.csv", lookups=[lookup], on=["sku"], columns=["name_lookup1", "sku"], rename={"sku": "id"})

    assert _rows("out.csv") == [
        {"name_lookup1": "x", "id": 1},
        {"name_lookup1": None, "id": 2},
        {"name_lookup1": None, "id": 3},
    ]
    assert report.to_dict()["target"]["columns"] == ["name_lookup1", "id"]


def test_modes_of_the_write(workdir: Path) -> None:
    join(MAIN, "out.csv", lookups=[PRICES], on=["sku"])
    join(MAIN, "out.csv", lookups=[PRICES], on=["sku"], mode="append")

    assert _keys("out.csv") == [1, 2, 3, 1, 2, 3]
    with pytest.raises(DataioError) as caught:
        join(MAIN, "out.csv", lookups=[PRICES], on=["sku"], mode="error")
    assert caught.value.code == "TARGET_EXISTS"


def test_replace_keeps_a_backup_that_restore_brings_back(workdir: Path) -> None:
    write(pd.DataFrame([{"old": 1}]), "out.csv")

    join(MAIN, "out.csv", lookups=[PRICES], on=["sku"])
    restore()

    assert _rows("out.csv") == [{"old": 1}]


@pytest.mark.parametrize("over", ["main", "lookup"])
def test_target_that_is_a_source_needs_overwrite(workdir: Path, over: str) -> None:
    write(pd.DataFrame(MAIN), "main.csv")
    write(pd.DataFrame(PRICES), "prices.csv")
    target = "main.csv" if over == "main" else "prices.csv"

    with pytest.raises(WriteOverSource):
        join("main.csv", target, lookups=["prices.csv"], on=["sku"])

    join("main.csv", target, lookups=["prices.csv"], on=["sku"], overwrite=True)
    assert _keys(target, "price") == [10, 20, None]


def test_dry_run_reports_the_counts_and_writes_nothing(workdir: Path) -> None:
    report = join(MAIN, "out.csv", lookups=[PRICES], on=["sku"], dry_run=True)

    assert not (workdir / "out.csv").exists()
    assert report.to_dict()["target"]["rows_after"] == 3
    assert report.to_dict()["lookups"][0]["matched"] == 2


def test_sources_as_addresses(workdir: Path) -> None:
    write(pd.DataFrame(MAIN), "main.csv")
    write(pd.DataFrame(PRICES), "prices.xlsx", sheet="Prices")

    report = join("main.csv", "out.csv", lookups=["prices.xlsx#Prices"], on=["sku"])

    assert _keys("out.csv", "price") == [10, 20, None]
    assert report.to_dict()["source"]["uri"] == "main.csv"
    assert report.to_dict()["lookups"][0]["uri"] == "prices.xlsx#Prices"


def test_sources_as_a_dataframe_and_records(workdir: Path) -> None:
    join(pd.DataFrame(MAIN), "out.csv", lookups=[PRICES], on=["sku"])

    assert _keys("out.csv", "price") == [10, 20, None]
