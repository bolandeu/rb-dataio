"""Target columns for many targets: templates (split_by, chunk_rows), batch convert and Google Sheets."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from rb_dataio import DataioError, convert, write

from .test_gsheet import FakeClient, client  # noqa: F401  (the fixture of the gsheet tests)

TABLE = pd.DataFrame({"region": ["n", "s", "n"], "a": ["1", "2", "3"], "b": ["4", "5", "6"]})


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, data_dir: Path) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def lines(path: Path) -> list[str]:
    return path.read_text().splitlines()


def test_split_keeps_only_the_chosen_columns(workdir: Path) -> None:
    write(TABLE, "out/{region}.csv", split_by="region", columns=["a"])

    assert lines(workdir / "out/n.csv") == ["a", "1", "3"]
    assert lines(workdir / "out/s.csv") == ["a", "2"]


def test_split_column_can_be_kept_and_renamed(workdir: Path) -> None:
    write(TABLE, "out/{region}.csv", split_by="region", columns=["region", "a"], rename={"region": "r"})

    assert lines(workdir / "out/n.csv") == ["r,a", "n,1", "n,3"]
    assert lines(workdir / "out/s.csv") == ["r,a", "s,2"]


def test_renaming_a_dropped_split_column_is_refused_and_nothing_is_written(workdir: Path) -> None:
    with pytest.raises(DataioError) as refused:
        write(TABLE, "out/{region}.csv", split_by="region", drop_split_column=True, rename={"region": "r"})

    assert (refused.value.code, refused.value.exit_code) == ("INVALID_ARGUMENTS", 2)
    assert "region" in refused.value.message
    assert not (workdir / "out").exists()


def test_drop_split_column_acts_as_if_it_were_not_in_columns(workdir: Path) -> None:
    write(TABLE, "out/{region}.csv", split_by="region", drop_split_column=True, columns=["region", "b", "a"])

    assert lines(workdir / "out/n.csv") == ["b,a", "4,1", "6,3"]


def test_a_wrong_name_is_refused_before_any_part_is_written(workdir: Path) -> None:
    with pytest.raises(DataioError) as refused:
        write(TABLE, "out/{region}.csv", split_by="region", columns=["a", "zz"])

    assert (refused.value.code, refused.value.exit_code) == ("INVALID_ARGUMENTS", 2)
    assert "zz" in refused.value.message
    assert not (workdir / "out").exists()


def test_chunks_keep_only_the_chosen_columns(workdir: Path) -> None:
    five = pd.DataFrame({"a": list("12345"), "b": list("abcde")})

    write(five, "out/part_{n}.csv", chunk_rows=2, columns=["b"])

    assert [lines(workdir / f"out/part_{n}.csv") for n in (1, 2, 3)] == [["b", "a", "b"], ["b", "c", "d"], ["b", "e"]]


@pytest.fixture
def sources(workdir: Path) -> Path:
    (workdir / "in").mkdir()
    for stem in "abc":
        (workdir / "in" / f"{stem}.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    return workdir


def test_batch_convert_shapes_each_output(sources: Path) -> None:
    report = convert("in/*.csv", "out/{stem}.json", columns=["a"], rename={"a": "x"})

    assert [target.uri for target in report.targets or []] == ["out/a.json", "out/b.json", "out/c.json"]
    for stem in "abc":
        assert [list(row) for row in json.loads((sources / f"out/{stem}.json").read_text())] == [["x"]]


def test_batch_convert_stops_on_a_source_without_the_column(sources: Path) -> None:
    (sources / "in" / "b.csv").write_text("z\n1\n", encoding="utf-8")

    with pytest.raises(DataioError) as refused:
        convert("in/*.csv", "out/{stem}.csv", columns=["a"])

    assert (refused.value.code, refused.value.exit_code) == ("INVALID_ARGUMENTS", 2)
    assert "a" in refused.value.message
    assert "in/b.csv" in refused.value.message


def test_batch_convert_keep_going_lists_the_failed_source(sources: Path) -> None:
    (sources / "in" / "b.csv").write_text("z\n1\n", encoding="utf-8")

    report = convert("in/*.csv", "out/{stem}.csv", columns=["a"], keep_going=True)

    assert [target.uri for target in report.targets or []] == ["out/a.csv", "out/c.csv"]
    assert [(error.uri, error.code) for error in report.errors or []] == [("in/b.csv", "INVALID_ARGUMENTS")]
    assert lines(sources / "out/a.csv") == ["a", "1"]


def test_a_gsheet_target_gets_the_chosen_columns(client: FakeClient) -> None:  # noqa: F811
    frame = pd.DataFrame({"a": ["1", "2"], "b": ["3", "4"]})

    write(frame, "gsheet://ID#New", columns=["b", "a"], rename={"b": "x"})

    assert client.sheet("New").values() == [["x", "a"], ["3", "1"], ["4", "2"]]
