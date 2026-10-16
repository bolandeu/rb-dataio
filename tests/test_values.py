"""Value normalisation through the public library API: NA words, empty cells, types, as_text, dtypes, headers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from rb_dataio import DataioError, convert, read

NA_WORDS = ["NA", "null", "nan", "None", "-"]


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, data_dir: Path) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def csv(workdir: Path, text: str, name: str = "a.csv") -> str:
    (workdir / name).write_text(text, encoding="utf-8")
    return name


# --- NA words and empty cells ----------------------------------------------------


def test_na_words_stay_strings(workdir: Path) -> None:
    frame = read(csv(workdir, "word\n" + "\n".join(NA_WORDS) + "\n"))
    assert frame["word"].tolist() == NA_WORDS


def test_empty_cell_is_missing_and_is_written_back_empty(workdir: Path) -> None:
    csv(workdir, "phrase,freq\nелка,\nпихта,3\n")
    assert read("a.csv")["freq"].isna().tolist() == [True, False]
    convert("a.csv", "b.csv")
    assert (workdir / "b.csv").read_text(encoding="utf-8") == "phrase,freq\nелка,\nпихта,3\n"


def test_rows_where_every_cell_is_empty_are_dropped(workdir: Path) -> None:
    frame = read(csv(workdir, "a,b\n1,2\n,\n\n3,4\n,\n"))
    assert frame.to_dict("list") == {"a": [1, 3], "b": [2, 4]}
    assert frame.index.tolist() == [0, 1]


# --- types ----------------------------------------------------------------------


@pytest.mark.parametrize("value", ["007", "+79001234567", "1234567890123456", "-007"])
def test_ids_stay_text(workdir: Path, value: str) -> None:
    frame = read(csv(workdir, f"id\n{value}\n5\n"))
    assert frame["id"].tolist() == [value, "5"]


def test_fifteen_digits_are_still_a_number(workdir: Path) -> None:
    assert read(csv(workdir, "id\n123456789012345\n"))["id"].tolist() == [123456789012345]


def test_integers_floats_and_dates_are_detected(workdir: Path) -> None:
    frame = read(csv(workdir, "n,x,d,t\n1,1.5,2024-01-05,abc\n2,2,2024-02-06,def\n3,0.25,2024-03-07,\n"))
    assert [str(dtype) for dtype in frame.dtypes] == ["int64", "float64", "datetime64[us]", "str"]
    assert frame["n"].tolist() == [1, 2, 3]
    assert frame["d"].dt.strftime("%Y-%m-%d").tolist() == ["2024-01-05", "2024-02-06", "2024-03-07"]


def test_integer_column_with_a_gap_stays_integer(workdir: Path) -> None:
    frame = read(csv(workdir, "a,n\nx,1\ny,\nz,3\n"))
    assert pd.api.types.is_integer_dtype(frame["n"])
    assert frame["n"].tolist()[0] == 1
    assert frame["n"].isna().tolist() == [False, True, False]


def test_as_text_makes_every_column_str(workdir: Path) -> None:
    frame = read(csv(workdir, "n,d\n1,2024-01-05\n2,2024-01-06\n"), as_text=True)
    assert [str(dtype) for dtype in frame.dtypes] == ["str", "str"]
    assert frame["n"].tolist() == ["1", "2"]


def test_dtypes_sets_one_column(workdir: Path) -> None:
    frame = read(csv(workdir, "freq,id\n007,007\n5,5\n"), dtypes={"freq": "int"})
    assert frame["freq"].tolist() == [7, 5]
    assert frame["id"].tolist() == ["007", "5"]


def test_value_that_cannot_convert_is_read_failed_naming_column_and_value(workdir: Path) -> None:
    with pytest.raises(DataioError) as caught:
        read(csv(workdir, "freq\n1\nmany\n"), dtypes={"freq": "int"})
    assert caught.value.code == "READ_FAILED"
    assert "'freq'" in caught.value.message
    assert "'many'" in caught.value.message
    assert "'a.csv'" in caught.value.message


def test_unknown_dtype_or_column_is_invalid(workdir: Path) -> None:
    csv(workdir, "freq\n1\n")
    for dtypes in ({"freq": "blob"}, {"nope": "int"}):
        with pytest.raises(DataioError) as caught:
            read("a.csv", dtypes=dtypes)
        assert caught.value.code == "INVALID_ARGUMENTS"


# --- header repair ----------------------------------------------------------------


def test_empty_and_duplicate_header_names_are_repaired_with_one_warning(workdir: Path) -> None:
    csv(workdir, ",phrase,phrase\nx,y,z\n")
    assert list(read("a.csv").columns) == ["col1", "phrase", "phrase_2"]
    warnings = convert("a.csv", "b.csv").warnings
    assert len(warnings) == 1
    assert "col1" in warnings[0] and "phrase_2" in warnings[0]
    assert (workdir / "b.csv").read_text(encoding="utf-8").startswith("col1,phrase,phrase_2\n")


def test_clean_header_has_no_warning(workdir: Path) -> None:
    csv(workdir, "a,b\n1,2\n")
    assert convert("a.csv", "b.csv").warnings == []


def test_header_false_names_columns_col1_to_colN(workdir: Path) -> None:
    frame = read(csv(workdir, "x,1\ny,2\n"), header=False)
    assert frame.to_dict("list") == {"col1": ["x", "y"], "col2": [1, 2]}
