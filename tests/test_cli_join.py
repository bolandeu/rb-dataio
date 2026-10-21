"""dataio join through the CLI under --json (CliRunner): the flags reach join(), its report and its refusals."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from rb_dataio import read

from .test_cli import invoke, invoke_json


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """main.csv (sku,name: 1,a / 2,b) and prices.csv (sku,price: 1,10), the current directory."""
    (tmp_path / "main.csv").write_text("sku,name\n1,a\n2,b\n", encoding="utf-8")
    (tmp_path / "prices.csv").write_text("sku,price\n1,10\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _rows(path: Path) -> list[list[object]]:
    table = read(str(path)).astype(object).where(lambda frame: frame.notna(), None)
    return [list(table.columns), *table.values.tolist()]


def test_left_join_reports_the_lookup_and_writes_the_columns(workdir: Path) -> None:
    code, payload = invoke_json("join", "main.csv", "out.csv", "--lookup", "prices.csv", "--on", "sku")

    assert code == 0
    assert payload["ok"] is True
    assert payload["lookups"] == [{"uri": "prices.csv", "rows": 1, "matched": 1, "unmatched": 1, "empty_keys": 0}]
    assert _rows(workdir / "out.csv") == [["sku", "name", "price"], [1, "a", 10], [2, "b", None]]


def test_human_report_shows_the_lookup_counts(workdir: Path) -> None:
    result = invoke("join", "main.csv", "out.csv", "--lookup", "prices.csv", "--on", "sku")

    assert result.exit_code == 0
    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)  # the gate may force colour
    assert "Lookup prices.csv: 1 rows, 1 matched, 1 unmatched, 0 empty keys" in plain


def test_keys_lookups_and_how_reach_join(workdir: Path) -> None:
    (workdir / "main.csv").write_text("sku,region,name\n1,eu,a\n2,us,b\n", encoding="utf-8")
    (workdir / "p1.csv").write_text("article,region,price\n1,eu,10\n3,us,30\n", encoding="utf-8")
    (workdir / "p2.csv").write_text("article,region,stock\n1,eu,5\n", encoding="utf-8")
    args = ["--lookup", "p1.csv", "--lookup", "p2.csv", "--on", "sku=article", "--on", "region"]

    code, payload = invoke_json("join", "main.csv", "out.csv", *args, "--how", "inner")

    assert code == 0
    assert [part["uri"] for part in payload["lookups"]] == ["p1.csv", "p2.csv"]
    assert _rows(workdir / "out.csv") == [["sku", "region", "name", "price", "stock"], [1, "eu", "a", 10, 5]]

    code, _ = invoke_json("join", "main.csv", "full.csv", *args, "--how", "full")

    assert code == 0
    assert len(_rows(workdir / "full.csv")) == 4  # the header, 1 matched, 2 unmatched main, 3 only in p1


def test_how_right_takes_the_lookup_rows(workdir: Path) -> None:
    code, _ = invoke_json("join", "main.csv", "out.csv", "--lookup", "prices.csv", "--on", "sku", "--how", "right")

    assert code == 0
    assert _rows(workdir / "out.csv") == [["sku", "name", "price"], [1, "a", 10]]


@pytest.mark.parametrize(
    ("args", "words"),
    [
        (["--lookup", "prices.csv"], ["on"]),
        (["--lookup", "prices.csv", "--on", "sku", "--how", "other"], ["other"]),
        (["--lookup", "prices.csv", "--lookup", "prices.csv", "--on", "sku", "--how", "right"], ["right"]),
        (["--lookup", "prices.csv", "--on", "zz"], ["zz", "main.csv", "sku, name"]),
        (["--lookup", "prices.csv", "--on", "name=zz"], ["zz", "prices.csv", "sku, price"]),
    ],
)
def test_wrong_arguments_are_refused_and_write_nothing(workdir: Path, args: list[str], words: list[str]) -> None:
    code, payload = invoke_json("join", "main.csv", "out.csv", *args)

    assert code == 2
    assert payload["error"]["code"] == "INVALID_ARGUMENTS"
    assert all(word in payload["error"]["message"] for word in words)
    assert not (workdir / "out.csv").exists()


def test_dry_run_reports_the_lookups_and_writes_nothing(workdir: Path) -> None:
    code, payload = invoke_json("join", "main.csv", "out.csv", "--lookup", "prices.csv", "--on", "sku", "--dry-run")

    assert code == 0
    assert payload["lookups"][0]["matched"] == 1
    assert not (workdir / "out.csv").exists()


def test_target_that_is_the_source_needs_confirm_and_keeps_a_backup(workdir: Path) -> None:
    args = ["join", "main.csv", "main.csv", "--lookup", "prices.csv", "--on", "sku"]

    code, payload = invoke_json(*args, "--non-interactive")

    assert code != 0
    assert payload["ok"] is False
    assert _rows(workdir / "main.csv") == [["sku", "name"], [1, "a"], [2, "b"]]

    code, payload = invoke_json(*args, "--confirm")

    assert code == 0
    assert _rows(workdir / "main.csv") == [["sku", "name", "price"], [1, "a", 10], [2, "b", None]]

    code, _ = invoke_json("restore", "--confirm")

    assert code == 0
    assert _rows(workdir / "main.csv") == [["sku", "name"], [1, "a"], [2, "b"]]


def test_stdout_target_is_the_data(workdir: Path) -> None:
    result = invoke("join", "main.csv", "-", "--lookup", "prices.csv", "--on", "sku")

    assert result.exit_code == 0
    assert result.stdout == "sku,name,price\n1,a,10\n2,b,\n"


def test_stdout_target_under_json_is_records_in_the_envelope(workdir: Path) -> None:
    code, payload = invoke_json("join", "main.csv", "-", "--lookup", "prices.csv", "--on", "sku")

    assert code == 0
    assert payload["data"] == [{"sku": 1, "name": "a", "price": 10}, {"sku": 2, "name": "b", "price": None}]
