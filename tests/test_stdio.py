"""stdin and stdout, the address `-`, through the CLI (CliRunner): the format of stdin from its content, stdout data."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from rb_dataio import read
from rb_dataio.cli import app

PHRASES = "phrase,freq\nкупить ёлку,10\nёлка цена,7\n"
runner = CliRunner()


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, data_dir: Path) -> Path:
    """A folder with a.csv (phrase,freq; 2 rows), the current directory, so addresses stay short."""
    (tmp_path / "a.csv").write_text(PHRASES, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def convert_json(*args: str, stdin: str | None = None) -> dict:
    result = runner.invoke(app, ["convert", *args, "--json"], input=stdin)
    lines = result.stdout.splitlines()
    assert len(lines) == 1, f"stdout must be one JSON object; got {result.stdout!r}, stderr {result.stderr!r}"
    assert result.exit_code == 0, result.stdout
    return json.loads(lines[0])


# --- stdin ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("stdin", "fmt", "delimiter"),
    [
        (PHRASES, "csv", ","),
        (PHRASES.replace(",", ";"), "csv", ";"),
        ('[{"phrase": "купить ёлку", "freq": 10}, {"phrase": "ёлка цена", "freq": 7}]', "json", None),
        ('{"phrase": "купить ёлку", "freq": 10}\n{"phrase": "ёлка цена", "freq": 7}\n', "jsonl", None),
    ],
    ids=["csv", "csv ;", "json", "jsonl"],
)
def test_format_of_stdin_is_detected_from_the_content(workdir: Path, stdin: str, fmt: str, delimiter: str) -> None:
    source = convert_json("-", "out.json", stdin=stdin)["source"]
    assert (source["uri"], source["format"], source["delimiter"]) == ("-", fmt, delimiter)
    assert read("out.json").to_dict("list") == {"phrase": ["купить ёлку", "ёлка цена"], "freq": [10, 7]}


def test_lines_without_a_stable_delimiter_are_text(workdir: Path) -> None:
    source = convert_json("-", "out.csv", stdin="купить ёлку, дёшево\nёлка\n\nпихта; цена\n")["source"]
    assert source["format"] == "txt"
    assert read("out.csv").to_dict("list") == {"text": ["купить ёлку, дёшево", "ёлка", "пихта; цена"]}


def test_format_flag_wins_over_the_content(workdir: Path) -> None:
    convert_json("-", "out.csv", "--in-format", "txt", stdin=PHRASES)
    assert read("out.csv")["text"].tolist() == PHRASES.splitlines()


# --- stdout -----------------------------------------------------------------------


def test_csv_goes_to_stdout(workdir: Path) -> None:
    result = runner.invoke(app, ["convert", "a.csv", "-"])
    assert result.exit_code == 0, result.stderr
    assert result.stdout == PHRASES


def test_one_column_goes_to_stdout_one_value_per_line(workdir: Path) -> None:
    (workdir / "p.csv").write_text("phrase\nкупить ёлку\nёлка цена\n", encoding="utf-8")
    result = runner.invoke(app, ["convert", "p.csv", "-"])
    assert result.stdout == "купить ёлку\nёлка цена\n"


def test_format_json_goes_to_stdout_as_json(workdir: Path) -> None:
    result = runner.invoke(app, ["convert", "a.csv", "-", "--out-format", "json"])
    assert json.loads(result.stdout) == [{"phrase": "купить ёлку", "freq": 10}, {"phrase": "ёлка цена", "freq": 7}]


def test_json_flag_puts_the_data_inside_the_envelope(workdir: Path) -> None:
    payload = convert_json("a.csv", "-")
    assert payload["ok"] is True
    assert payload["data"] == [{"phrase": "купить ёлку", "freq": 10}, {"phrase": "ёлка цена", "freq": 7}]
    assert payload["target"] == {
        "uri": "-",
        "format": "records",
        "mode": "replace",
        "rows": 2,
        "columns": ["phrase", "freq"],
    }


def test_stdin_to_stdout_under_json(workdir: Path) -> None:
    payload = convert_json("-", "-", stdin="ёлка\nпихта\n")
    assert payload["data"] == [{"text": "ёлка"}, {"text": "пихта"}]
