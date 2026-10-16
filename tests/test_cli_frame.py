"""The core frame through the CLI: convert, info, formats, backups under --json (CliRunner); restore: test_backup.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from rb_dataio import DataioError, read
from rb_dataio.cli import app

PHRASES = "phrase,freq\nкупить ёлку,10\nёлка цена,7\nискусственная ёлка,3\n"
runner = CliRunner()


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A folder with a.csv (phrase,freq; 3 rows), the current directory, so addresses stay short."""
    (tmp_path / "a.csv").write_text(PHRASES, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def invoke_json(*args: str) -> tuple[int, dict]:
    result = runner.invoke(app, [*args, "--json"])
    lines = result.stdout.splitlines()
    assert len(lines) == 1, f"stdout must be one JSON object; got {result.stdout!r}, stderr {result.stderr!r}"
    return result.exit_code, json.loads(lines[0])


# --- convert --------------------------------------------------------------------


def test_convert_json_is_the_report(workdir: Path) -> None:
    code, payload = invoke_json("convert", "a.csv", "b.csv")
    assert code == 0
    assert payload == {
        "ok": True,
        "source": {
            "uri": "a.csv",
            "format": "csv",
            "encoding": "utf-8",
            "delimiter": ",",
            "rows": 3,
            "columns": ["phrase", "freq"],
        },
        "target": {"uri": "b.csv", "format": "csv", "mode": "replace", "rows": 3, "columns": ["phrase", "freq"]},
        "warnings": [],
    }
    assert (workdir / "b.csv").read_text(encoding="utf-8") == PHRASES


def test_convert_missing_source_is_the_error_envelope(workdir: Path) -> None:
    code, payload = invoke_json("convert", "missing.csv", "b.csv")
    assert code == 2
    assert payload["ok"] is False
    assert payload["error"]["code"] == "SOURCE_NOT_FOUND"
    assert "'missing.csv'" in payload["error"]["message"]
    assert payload["error"]["action"] == "Pass format='text' to read the string as text"


def test_unknown_format_names_the_known_ones(workdir: Path) -> None:
    (workdir / "notes.xyz").write_text("whatever\n", encoding="utf-8")
    with pytest.raises(DataioError) as caught:
        read("notes.xyz")
    assert caught.value.code == "FORMAT_UNKNOWN"
    assert "csv" in (caught.value.action or "")

    code, payload = invoke_json("convert", "notes.xyz", "b.csv")
    assert code == 2
    assert payload["error"]["code"] == "FORMAT_UNKNOWN"
    assert "csv" in payload["error"]["action"]


def test_convert_limit_cuts_the_target(workdir: Path) -> None:
    code, payload = invoke_json("convert", "a.csv", "b.csv", "--limit", "2")
    assert code == 0
    assert payload["target"]["rows"] == 2
    assert (workdir / "b.csv").read_text(encoding="utf-8") == "phrase,freq\nкупить ёлку,10\nёлка цена,7\n"


@pytest.mark.parametrize("where", ["command", "global"])
def test_convert_dry_run_writes_nothing(workdir: Path, where: str) -> None:
    args = (
        ["convert", "a.csv", "b.csv", "--dry-run"] if where == "command" else ["--dry-run", "convert", "a.csv", "b.csv"]
    )
    code, payload = invoke_json(*args)
    assert code == 0
    assert payload["target"]["rows"] == 3
    assert payload["source"]["rows"] == 3
    assert not (workdir / "b.csv").exists()


def test_convert_options_reach_both_sides(workdir: Path) -> None:
    (workdir / "win.csv").write_bytes("phrase;freq\nёлка;5\n".encode("cp1251"))
    code, payload = invoke_json(
        "convert",
        "win.csv",
        "out.csv",
        "--in-encoding",
        "cp1251",
        "--in-sep",
        ";",
        "--out-sep",
        "|",
        "--mode",
        "replace",
    )
    assert code == 0
    assert (payload["source"]["encoding"], payload["source"]["delimiter"]) == ("cp1251", ";")
    assert (workdir / "out.csv").read_text(encoding="utf-8") == "phrase|freq\nёлка|5\n"


def test_dtypes_flag_needs_column_equals_type(workdir: Path) -> None:
    code, payload = invoke_json("convert", "a.csv", "b.csv", "--dtypes", "freq")
    assert code == 2
    assert payload["error"]["code"] == "INVALID_ARGUMENTS"
    code, _ = invoke_json("convert", "a.csv", "b.csv", "--dtypes", "freq=int", "--dtypes", "phrase=str")
    assert code == 0


def test_convert_human_output_names_both_sides(workdir: Path) -> None:
    result = runner.invoke(app, ["convert", "a.csv", "b.csv"])
    assert result.exit_code == 0
    assert [line.strip() for line in result.stdout.splitlines()][:2] == ["Source", "uri: a.csv"]


# --- info / formats -------------------------------------------------------------


def test_info_json_describes_the_source(workdir: Path) -> None:
    rows = "".join(f"фраза {n},{n}\n" for n in range(7))
    (workdir / "big.csv").write_text("phrase,freq\n" + rows, encoding="utf-8")
    code, payload = invoke_json("info", "big.csv")
    assert code == 0
    assert payload["source"]["format"] == "csv"
    assert payload["source"]["rows"] == 7
    assert payload["types"] == {"phrase": "str", "freq": "int64"}
    assert payload["preview"] == [{"phrase": f"фраза {n}", "freq": n} for n in range(5)]


def test_info_human_output(workdir: Path) -> None:
    result = runner.invoke(app, ["info", "a.csv"])
    assert result.exit_code == 0
    assert [line.strip() for line in result.stdout.splitlines()][:2] == ["Source", "uri: a.csv"]


def test_formats_json_lists_every_format() -> None:
    code, payload = invoke_json("formats")
    assert code == 0
    assert {
        "name": "csv",
        "extensions": [".csv"],
        "read": True,
        "write": True,
        "append": False,
        "options": ["encoding", "sep"],
    } in payload["formats"]


def test_formats_human_output() -> None:
    result = runner.invoke(app, ["formats"])
    assert result.exit_code == 0
    assert "csv" in result.stdout.split()


# --- backups -------------------------------------------------------------------


def test_backups_is_an_empty_list(data_dir: Path) -> None:
    assert invoke_json("backups") == (0, {"ok": True, "backups": []})
    assert runner.invoke(app, ["backups"]).exit_code == 0
