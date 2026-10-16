"""Split one table into many targets: `write()` and `convert` under --json with a template target.

The user data dir is a temporary folder (the `data_dir` fixture), so the backup store starts empty.
"""

from __future__ import annotations

import json
from pathlib import Path

import openpyxl
import pandas as pd
import pytest
from typer.testing import CliRunner

from rb_dataio import DataioError, backups, read, restore, write
from rb_dataio.cli import app

runner = CliRunner()
REGIONS = pd.DataFrame({"region": ["msk", "spb", "msk"], "city": ["a", "b", "c"]})


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, data_dir: Path) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_split_by_column_writes_one_file_per_value(workdir: Path) -> None:
    report = write(REGIONS, "out/{region}.csv", split_by="region")

    assert (workdir / "out/msk.csv").read_text() == "region,city\nmsk,a\nmsk,c\n"
    assert (workdir / "out/spb.csv").read_text() == "region,city\nspb,b\n"
    assert [(t.uri, t.rows) for t in report.targets] == [("out/msk.csv", 2), ("out/spb.csv", 1)]


def test_drop_split_column_leaves_it_out(workdir: Path) -> None:
    write(REGIONS, "out/{region}.csv", split_by="region", drop_split_column=True)

    assert (workdir / "out/msk.csv").read_text() == "city\na\nc\n"
    assert (workdir / "out/spb.csv").read_text() == "city\nb\n"


def test_split_into_sheets_of_one_book(workdir: Path) -> None:
    write(REGIONS, "book.xlsx#{region}", split_by="region")

    book = openpyxl.load_workbook(workdir / "book.xlsx")
    assert book.sheetnames == ["msk", "spb"]
    assert [[cell.value for cell in row] for row in book["msk"].iter_rows()] == [
        ["region", "city"],
        ["msk", "a"],
        ["msk", "c"],
    ]


def test_chunk_rows_writes_numbered_parts(workdir: Path) -> None:
    frame = pd.DataFrame({"x": range(25_000)})

    report = write(frame, "out/part_{n}.csv", chunk_rows=10_000)

    assert [(t.uri, t.rows) for t in report.targets] == [
        ("out/part_1.csv", 10_000),
        ("out/part_2.csv", 10_000),
        ("out/part_3.csv", 5_000),
    ]
    assert len(read("out/part_3.csv")) == 5_000


def test_file_names_are_made_safe_and_reported(workdir: Path) -> None:
    frame = pd.DataFrame({"region": ["a/b:c*"], "v": [1]})

    report = write(frame, "out/{region}.csv", split_by="region")

    assert [t.uri for t in report.targets] == ["out/a_b_c_.csv"]
    assert (workdir / "out/a_b_c_.csv").exists()


def test_sheet_names_are_made_safe_and_short(workdir: Path) -> None:
    frame = pd.DataFrame({"region": ["x[1]:y?" + "z" * 40], "v": [1]})

    report = write(frame, "book.xlsx#{region}", split_by="region")

    (sheet,) = openpyxl.load_workbook(workdir / "book.xlsx").sheetnames
    assert sheet == "x_1__y_" + "z" * 24
    assert len(sheet) == 31
    assert [t.uri for t in report.targets] == [f"book.xlsx#{sheet}"]


def test_replaced_files_have_a_backup_each_and_restore_per_file(workdir: Path) -> None:
    (workdir / "out").mkdir()
    (workdir / "out/msk.csv").write_text("region,city\nold,x\n")
    (workdir / "out/spb.csv").write_text("region,city\nold,y\n")

    write(REGIONS, "out/{region}.csv", split_by="region")

    kept = backups()
    assert sorted(Path(entry.target).name for entry in kept) == ["msk.csv", "spb.csv"]
    msk = next(entry for entry in kept if entry.target.endswith("msk.csv"))
    restore(msk.id)
    assert (workdir / "out/msk.csv").read_text() == "region,city\nold,x\n"
    assert (workdir / "out/spb.csv").read_text() == "region,city\nspb,b\n"


def test_dry_run_plans_every_target_and_writes_nothing(workdir: Path) -> None:
    report = write(REGIONS, "out/{region}.csv", split_by="region", dry_run=True)

    assert [(t.uri, t.exists, t.rows_after) for t in report.targets] == [
        ("out/msk.csv", False, 2),
        ("out/spb.csv", False, 1),
    ]
    assert not (workdir / "out").exists()


def test_a_failed_target_stops_the_split_unless_keep_going(workdir: Path) -> None:
    (workdir / "out").mkdir()
    (workdir / "out/msk.csv").write_text("old\n")

    with pytest.raises(DataioError) as stopped:
        write(REGIONS, "out/{region}.csv", split_by="region", mode="error")
    assert stopped.value.code == "TARGET_EXISTS"
    assert not (workdir / "out/spb.csv").exists()

    report = write(REGIONS, "out/{region}.csv", split_by="region", mode="error", keep_going=True)
    assert [t.uri for t in report.targets] == ["out/spb.csv"]
    assert [(e.uri, e.code) for e in report.errors] == [("out/msk.csv", "TARGET_EXISTS")]


@pytest.mark.parametrize(
    ("target", "options"),
    [
        ("out/{region}.csv", {}),
        ("out/{region}.csv", {"split_by": "region", "chunk_rows": 2}),
        ("out/{region}.csv", {"split_by": "nope"}),
        ("out/{city}.csv", {"split_by": "region"}),
        ("out/{n}.csv", {"split_by": "region"}),
        ("out/{region}.csv", {"chunk_rows": 2}),
        ("out.xlsx#{region}", {"split_by": "region", "sheet": "S"}),
    ],
)
def test_a_template_the_options_do_not_fit_is_invalid(workdir: Path, target: str, options: dict) -> None:
    with pytest.raises(DataioError) as refused:
        write(REGIONS, target, **options)
    assert refused.value.code == "INVALID_ARGUMENTS"


def test_two_values_with_one_safe_name_are_refused(workdir: Path) -> None:
    frame = pd.DataFrame({"region": ["a/b", "a:b"], "v": [1, 2]})

    with pytest.raises(DataioError) as refused:
        write(frame, "out/{region}.csv", split_by="region")
    assert refused.value.code == "INVALID_ARGUMENTS"
    assert not (workdir / "out").exists()


def test_convert_cli_splits_and_reports_targets(workdir: Path) -> None:
    REGIONS.to_csv("in.csv", index=False)

    result = runner.invoke(
        app, ["convert", "in.csv", "out/{region}.csv", "--split-by", "region", "--drop-split-column", "--json"]
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert [t["uri"] for t in payload["targets"]] == ["out/msk.csv", "out/spb.csv"]
    assert (workdir / "out/spb.csv").read_text() == "city\nb\n"
