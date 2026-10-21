"""dataio convert --columns / --rename through the CLI, and the docs that describe the target columns."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest
from typer.testing import CliRunner

from rb_dataio.cli import app

ROOT = Path(__file__).parents[1]
runner = CliRunner()


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A folder with in.csv (phrase,match,similarity), the current directory."""
    (tmp_path / "in.csv").write_text("phrase,match,similarity\nелка,1,0.5\nпалка,2,0.7\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_columns_and_rename_to_json(workdir: Path) -> None:
    result = runner.invoke(
        app, ["convert", "in.csv", "out.json", "--columns", "phrase,similarity", "--rename", "similarity=сходство"]
    )

    assert result.exit_code == 0
    records = json.loads((workdir / "out.json").read_text(encoding="utf-8"))
    assert [list(record) for record in records] == [["phrase", "сходство"]] * 2


def test_repeated_options_keep_the_given_order(workdir: Path) -> None:
    args = ["--columns", "similarity", "--columns", "phrase", "--rename", "phrase=p", "--rename", "similarity=s"]
    result = runner.invoke(app, ["convert", "in.csv", "out.csv", *args])

    assert result.exit_code == 0
    assert (workdir / "out.csv").read_text(encoding="utf-8").splitlines()[0] == "s,p"


def test_rename_list_and_first_equals(workdir: Path) -> None:
    runner.invoke(app, ["convert", "in.csv", "a.csv", "--rename", "phrase=x,match=y"])
    runner.invoke(app, ["convert", "in.csv", "b.csv", "--rename", "phrase=b=c"])

    assert (workdir / "a.csv").read_text(encoding="utf-8").splitlines()[0] == "x,y,similarity"
    assert (workdir / "b.csv").read_text(encoding="utf-8").splitlines()[0] == "b=c,match,similarity"


def test_wrong_column_is_refused(workdir: Path) -> None:
    result = runner.invoke(app, ["convert", "in.csv", "out.json", "--columns", "phrase,zz", "--json"])

    assert result.exit_code == 2
    error = json.loads(result.stdout)["error"]
    assert error["code"] == "INVALID_ARGUMENTS"
    assert "zz" in error["message"]
    assert "phrase, match, similarity" in error["message"]
    assert not (workdir / "out.json").exists()


def test_wrong_column_is_refused_in_human_mode(workdir: Path) -> None:
    result = runner.invoke(app, ["convert", "in.csv", "out.json", "--columns", "zz"])

    assert result.exit_code == 2
    assert not (workdir / "out.json").exists()


def test_rename_without_equals_shows_the_form(workdir: Path) -> None:
    result = runner.invoke(app, ["convert", "in.csv", "out.csv", "--rename", "similarity", "--json"])

    assert result.exit_code == 2
    assert "old=new" in json.loads(result.stdout)["error"]["message"]


def test_stdout_with_one_column_is_plain_text(workdir: Path) -> None:
    result = runner.invoke(app, ["convert", "in.csv", "-", "--columns", "phrase"])

    assert result.exit_code == 0
    assert result.stdout == "елка\nпалка\n"


@pytest.mark.parametrize("args", [["describe"], ["convert", "--help"]])
def test_describe_and_help_show_both_options(args: list[str]) -> None:
    text = runner.invoke(app, args).stdout

    assert "--columns" in text
    assert "--rename" in text


def test_describe_and_help_are_the_same_in_ci(same_in_ci: Callable[[str], None]) -> None:
    same_in_ci("test_describe_and_help_show_both_options")


def test_docs_describe_the_target_columns() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    spec = (ROOT / "docs" / "SPEC.md").read_text(encoding="utf-8")
    out_of_scope = spec.split("## Out of Scope", 1)[1]

    assert "columns=[" in readme
    assert "rename={" in readme
    assert "dataio convert" in readme
    assert "--columns" in readme
    assert "target columns" in spec.split("### Writing", 1)[1].split("###", 1)[0]
    assert "column" in out_of_scope and "read" in out_of_scope
