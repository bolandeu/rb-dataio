"""Protection of a write through the library (write, convert): the atomic write, the write modes,
the write over the source, the loss warnings and the dry run; the write over the source through the CLI too.

The user data dir is a temporary folder (the `data_dir` fixture), so the backup store starts empty.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from rb_dataio import DataioError, backups, convert, write
from rb_dataio.cli import app

PHRASES = "phrase,freq\nкупить ёлку,10\nёлка цена,7\nискусственная ёлка,3\n"


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, data_dir: Path) -> Path:
    """A folder with a.csv (phrase,freq; 3 rows), the current directory; the backup store is empty."""
    folder = tmp_path / "work"
    folder.mkdir()
    (folder / "a.csv").write_text(PHRASES, encoding="utf-8")
    monkeypatch.chdir(folder)
    return folder


# --- the atomic write -----------------------------------------------------------


def test_a_write_that_fails_midway_leaves_the_old_file_intact(workdir: Path) -> None:
    old = (workdir / "a.csv").read_bytes()
    # ASCII cannot hold the last row: pandas writes the first rows, then fails on it.
    frame = pd.DataFrame({"phrase": ["tree"] * 200_000 + ["ёлка"]})
    with pytest.raises(DataioError) as caught:
        write(frame, "a.csv", encoding="ascii")
    assert caught.value.code == "WRITE_FAILED"
    assert (workdir / "a.csv").read_bytes() == old
    assert sorted(path.name for path in workdir.iterdir()) == ["a.csv"]
    assert backups() == []


WRITER = """
import sys
import pandas as pd
from rb_dataio import write

letter, target, times = sys.argv[1], sys.argv[2], int(sys.argv[3])
frame = pd.DataFrame({"value": [letter * 20] * 50_000})
for _ in range(times):
    write(frame, target)
"""


def test_two_processes_writing_one_target_leave_one_complete_version(workdir: Path) -> None:
    times = 5
    writers = [
        subprocess.Popen([sys.executable, "-c", WRITER, letter, str(workdir / "a.csv"), str(times)])  # noqa: S603
        for letter in "ab"
    ]
    assert [writer.wait(timeout=120) for writer in writers] == [0, 0]
    versions = {"value\n" + f"{letter * 20}\n" * 50_000 for letter in "ab"}
    assert (workdir / "a.csv").read_text(encoding="utf-8") in versions
    assert len(backups()) == 2 * times
    assert sorted(path.name for path in workdir.iterdir()) == ["a.csv"]


# --- write modes ----------------------------------------------------------------


def test_mode_error_refuses_an_existing_target(workdir: Path) -> None:
    with pytest.raises(DataioError) as caught:
        write(pd.DataFrame({"x": [1]}), "a.csv", mode="error")
    assert (caught.value.code, caught.value.exit_code) == ("TARGET_EXISTS", 1)
    assert (workdir / "a.csv").read_text(encoding="utf-8") == PHRASES


def test_mode_error_writes_a_missing_target(workdir: Path) -> None:
    write(pd.DataFrame({"x": [1]}), "b.csv", mode="error")
    assert (workdir / "b.csv").read_text(encoding="utf-8") == "x\n1\n"


# --- the write over the source --------------------------------------------------


def test_convert_over_the_source_needs_overwrite(workdir: Path) -> None:
    with pytest.raises(DataioError) as caught:
        convert("a.csv", "a.csv", out_sep=";")
    assert (caught.value.code, caught.value.exit_code) == ("TARGET_EXISTS", 1)
    assert caught.value.action == "Pass overwrite=True / --confirm to write over the source; a backup is kept."
    assert (workdir / "a.csv").read_text(encoding="utf-8") == PHRASES
    assert backups() == []


def test_convert_over_the_source_by_another_path_needs_overwrite(workdir: Path) -> None:
    with pytest.raises(DataioError) as caught:
        convert("a.csv", str(workdir / "a.csv"))
    assert caught.value.code == "TARGET_EXISTS"


def test_convert_over_the_source_with_overwrite_keeps_a_backup(workdir: Path) -> None:
    convert("a.csv", "a.csv", out_sep=";", overwrite=True)
    assert (workdir / "a.csv").read_text(encoding="utf-8") == PHRASES.replace(",", ";")
    [entry] = backups()
    assert (entry.target, entry.rows) == (str(workdir / "a.csv"), 3)


def test_cli_convert_over_the_source_without_confirm_is_refused_under_non_interactive(workdir: Path) -> None:
    result = CliRunner().invoke(app, ["--non-interactive", "convert", "a.csv", "a.csv", "--json"])
    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["code"] == "INVALID_ARGUMENTS"
    assert (workdir / "a.csv").read_text(encoding="utf-8") == PHRASES
    assert backups() == []


def test_cli_convert_over_the_source_with_confirm_keeps_a_backup(workdir: Path) -> None:
    result = CliRunner().invoke(app, ["convert", "a.csv", "a.csv", "--out-sep", ";", "--confirm", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["target"]["rows"] == 3
    assert (workdir / "a.csv").read_text(encoding="utf-8") == PHRASES.replace(",", ";")
    assert [entry.rows for entry in backups()] == [3]


def test_cli_convert_over_the_source_asks_first(workdir: Path) -> None:
    declined = CliRunner().invoke(app, ["convert", "a.csv", "a.csv", "--out-sep", ";"], input="n\n")
    assert declined.exit_code == 1
    assert (workdir / "a.csv").read_text(encoding="utf-8") == PHRASES
    accepted = CliRunner().invoke(app, ["convert", "a.csv", "a.csv", "--out-sep", ";"], input="y\n")
    assert accepted.exit_code == 0
    assert (workdir / "a.csv").read_text(encoding="utf-8") == PHRASES.replace(",", ";")
    assert len(backups()) == 1


# --- loss warnings --------------------------------------------------------------


def test_a_replace_that_drops_most_rows_warns(workdir: Path) -> None:
    write(pd.DataFrame({"n": range(10_000)}), "out.csv")
    report = write(pd.DataFrame({"n": range(12)}), "out.csv").to_dict()
    assert report["warnings"] == ["replacing 10000 rows with 12"]


def test_a_replace_that_keeps_half_the_rows_does_not_warn(workdir: Path) -> None:
    write(pd.DataFrame({"n": range(10)}), "out.csv")
    assert write(pd.DataFrame({"n": range(5)}), "out.csv").warnings == []


def test_a_replace_that_loses_columns_names_them(workdir: Path) -> None:
    frame = pd.DataFrame({"phrase": ["a", "b", "c"]})
    assert write(frame, "a.csv").warnings == ["columns lost: freq"]


# --- dry run --------------------------------------------------------------------


def test_dry_run_shows_what_would_be_replaced(workdir: Path) -> None:
    (workdir / "b.csv").write_text("phrase,freq\nель,1\n", encoding="utf-8")
    report = convert("a.csv", "b.csv", dry_run=True).to_dict()
    assert report["target"] == {
        "uri": "b.csv",
        "format": "csv",
        "mode": "replace",
        "rows": 3,
        "columns": ["phrase", "freq"],
        "exists": True,
        "rows_before": 1,
        "rows_after": 3,
    }
    assert (workdir / "b.csv").read_text(encoding="utf-8") == "phrase,freq\nель,1\n"
    assert backups() == []


def test_dry_run_of_a_missing_target(workdir: Path) -> None:
    report = convert("a.csv", "b.csv", dry_run=True).to_dict()
    assert (report["target"]["exists"], report["target"]["rows_before"], report["target"]["rows_after"]) == (
        False,
        0,
        3,
    )
    assert not (workdir / "b.csv").exists()


def test_dry_run_over_the_source_is_not_refused(workdir: Path) -> None:
    report = convert("a.csv", "a.csv", dry_run=True).to_dict()
    assert report["target"]["exists"] is True
    assert (workdir / "a.csv").read_text(encoding="utf-8") == PHRASES
