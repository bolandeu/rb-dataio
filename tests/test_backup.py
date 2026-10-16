"""Backups and restore: through the library (write, backups, restore) and the CLI under --json (CliRunner).

The user data dir is a temporary folder (the `data_dir` fixture), so the store starts empty.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from rb_dataio import DataioError, backups, restore, write
from rb_dataio.cli import app

OLD = "phrase,freq\nёлка,5\nель,2\n"
NEW = pd.DataFrame({"phrase": ["сосна", "пихта", "кедр"], "freq": [1, 2, 3]})
NEW_TEXT = "phrase,freq\nсосна,1\nпихта,2\nкедр,3\n"
MB = 2**20
runner = CliRunner()


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, data_dir: Path) -> Path:
    """A folder with out.csv (2 rows), the current directory; the backup store is empty."""
    folder = tmp_path / "work"
    folder.mkdir()
    (folder / "out.csv").write_text(OLD, encoding="utf-8")
    monkeypatch.chdir(folder)
    return folder


def invoke_json(*args: str) -> tuple[int, dict]:
    result = runner.invoke(app, [*args, "--json"])
    lines = result.stdout.splitlines()
    assert len(lines) == 1, f"stdout must be one JSON object; got {result.stdout!r}, stderr {result.stderr!r}"
    return result.exit_code, json.loads(lines[0])


def sparse(path: Path, size_mb: int) -> None:
    """A file of `size_mb` MB that takes no disk space and that nobody can read.

    Unreadable, so dataio does not spend time counting the rows of half a gigabyte of zeros.
    """
    path.unlink(missing_ok=True)
    with path.open("wb") as file:
        file.truncate(size_mb * MB)
    path.chmod(0)


# --- the backup of a replace ----------------------------------------------------


def test_replace_keeps_a_backup_of_the_old_content(workdir: Path) -> None:
    before = datetime.now(UTC).replace(microsecond=0)
    write(NEW, "out.csv")
    [entry] = backups()
    assert entry.id
    assert before <= datetime.fromisoformat(entry.time) <= datetime.now(UTC)
    assert entry.target == str(workdir / "out.csv")
    assert entry.rows == 2
    assert (workdir / "out.csv").read_text(encoding="utf-8") == NEW_TEXT
    restore(entry.id)
    assert (workdir / "out.csv").read_text(encoding="utf-8") == OLD


def test_a_new_target_has_no_backup(workdir: Path) -> None:
    write(NEW, "fresh.csv")
    assert backups() == []


def test_restore_takes_the_newest_backup_and_backs_up_the_current_content(workdir: Path) -> None:
    write(NEW, "out.csv")
    write(pd.DataFrame({"phrase": ["дуб"], "freq": [9]}), "out.csv")
    report = restore().to_dict()
    assert (workdir / "out.csv").read_text(encoding="utf-8") == NEW_TEXT
    assert report["target"]["uri"] == str(workdir / "out.csv")
    assert report["target"]["rows"] == 3
    newest = backups()[0]
    assert newest.rows == 1
    restore(newest.id)
    assert (workdir / "out.csv").read_text(encoding="utf-8") == "phrase,freq\nдуб,9\n"


# --- the CLI --------------------------------------------------------------------


def test_backups_json_lists_the_entry(workdir: Path) -> None:
    write(NEW, "out.csv")
    [entry] = backups()
    code, payload = invoke_json("backups")
    assert code == 0
    assert payload == {"ok": True, "backups": [entry.to_dict()]}
    assert payload["backups"][0]["target"] == str(workdir / "out.csv")


def test_backups_human_output_names_the_entry(workdir: Path) -> None:
    write(NEW, "out.csv")
    [entry] = backups()
    result = runner.invoke(app, ["backups"])
    assert result.exit_code == 0
    assert result.stdout.split()[0] == entry.id


def test_restore_confirm_brings_the_old_content_back(workdir: Path) -> None:
    write(NEW, "out.csv")
    [entry] = backups()
    code, payload = invoke_json("restore", "--confirm")
    assert code == 0
    assert payload["backup"] == entry.to_dict()
    assert (workdir / "out.csv").read_text(encoding="utf-8") == OLD
    newest, oldest = backups()
    assert oldest == entry
    assert newest.rows == 3
    restore(newest.id)
    assert (workdir / "out.csv").read_text(encoding="utf-8") == NEW_TEXT


def test_restore_without_confirm_is_refused_under_non_interactive(workdir: Path) -> None:
    write(NEW, "out.csv")
    kept = backups()
    result = runner.invoke(app, ["--non-interactive", "restore", "--json"])
    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["code"] == "INVALID_ARGUMENTS"
    assert (workdir / "out.csv").read_text(encoding="utf-8") == NEW_TEXT
    assert backups() == kept


def test_restore_dry_run_shows_what_would_be_restored(workdir: Path) -> None:
    write(NEW, "out.csv")
    kept = backups()
    code, payload = invoke_json("restore", "--dry-run")
    assert code == 0
    assert payload["backup"] == kept[0].to_dict()
    assert payload["target"] == {
        "uri": str(workdir / "out.csv"),
        "format": "csv",
        "mode": "replace",
        "rows": 2,
        "columns": ["phrase", "freq"],
        "exists": True,
        "rows_before": 3,
        "rows_after": 2,
    }
    assert (workdir / "out.csv").read_text(encoding="utf-8") == NEW_TEXT
    assert backups() == kept


def test_restore_human_output_names_the_target(workdir: Path) -> None:
    write(NEW, "out.csv")
    result = runner.invoke(app, ["restore", "--confirm"], env={"COLUMNS": "400"})
    assert result.exit_code == 0
    assert f"uri: {workdir / 'out.csv'}" in [line.strip() for line in result.stdout.splitlines()]


def test_unknown_backup_id_lists_the_available_ids(workdir: Path) -> None:
    write(NEW, "out.csv")
    write(NEW, "out.csv")
    ids = [entry.id for entry in backups()]
    code, payload = invoke_json("restore", "nope", "--confirm")
    assert code == 2
    assert payload["error"]["code"] == "SOURCE_NOT_FOUND"
    assert payload["error"]["action"] == f"Pass one of the kept backup ids: {', '.join(ids)}."


def test_restore_with_no_backups_is_source_not_found(workdir: Path) -> None:
    with pytest.raises(DataioError) as caught:
        restore()
    assert (caught.value.code, caught.value.exit_code) == ("SOURCE_NOT_FOUND", 2)
    assert (workdir / "out.csv").read_text(encoding="utf-8") == OLD


# --- no backup ------------------------------------------------------------------


def test_backup_false_keeps_no_backup(workdir: Path) -> None:
    write(NEW, "out.csv", backup=False)
    assert backups() == []
    assert (workdir / "out.csv").read_text(encoding="utf-8") == NEW_TEXT


def test_no_backup_flag_keeps_no_backup(workdir: Path) -> None:
    (workdir / "a.csv").write_text(NEW_TEXT, encoding="utf-8")
    code, _ = invoke_json("convert", "a.csv", "out.csv", "--no-backup")
    assert code == 0
    assert backups() == []


# --- limits ---------------------------------------------------------------------


def test_the_51st_entry_prunes_the_oldest(workdir: Path) -> None:
    for n in range(51):
        write(pd.DataFrame({"n": [n]}), "out.csv")
    kept = backups()
    assert len(kept) == 50
    assert kept[-1].rows == 1  # the first backup (OLD, 2 rows) is gone
    restore(kept[-1].id)
    assert (workdir / "out.csv").read_text(encoding="utf-8") == "n\n0\n"


def test_an_entry_older_than_14_days_is_pruned(workdir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    now = time.time()
    monkeypatch.setattr(time, "time", lambda: now - timedelta(days=15).total_seconds())
    write(NEW, "out.csv")
    monkeypatch.setattr(time, "time", lambda: now)
    assert len(backups()) == 1
    write(NEW, "out.csv")
    [entry] = backups()
    assert entry.rows == 3


def test_more_than_2_gb_prunes_the_oldest(workdir: Path) -> None:
    for _ in range(5):  # 5 x 410 MB = 2050 MB, over 2048 MB
        sparse(workdir / "out.csv", 410)
        write(NEW, "out.csv")
    assert len(backups()) == 4


def test_an_object_over_500_mb_is_not_copied(workdir: Path) -> None:
    sparse(workdir / "out.csv", 501)
    report = write(NEW, "out.csv").to_dict()
    assert backups() == []
    assert report["warnings"] == ["no backup of 'out.csv': it is 501 MB, over the 500 MB limit"]
    assert (workdir / "out.csv").stat().st_size == len(NEW_TEXT.encode())
