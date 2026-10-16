"""The batch surface of the core: its parameters, the batch report, SCHEMA_MISMATCH and the three seams.

The behaviour modules (sources, targets, batch) answer "no" to every address for now; the tests patch them
to claim one, which proves the pipelines ask them. The merge, the split and the batch convert come with later tasks.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

import rb_dataio
from rb_dataio import DataioError, convert, read, write
from rb_dataio.cli import app
from rb_dataio.core.dataio import batch, sources, targets
from rb_dataio.core.dataio.options import ReadOptions, WriteOptions
from rb_dataio.core.dataio.report import BatchError, BatchTarget, PlannedBatchTarget, Report, SourcePart
from rb_dataio.core.errors import SchemaMismatch

runner = CliRunner()


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "a.csv").write_text("x,y\n1,2\n3,4\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def invoke_json(*args: str) -> tuple[int, dict]:
    result = runner.invoke(app, [*args, "--json"])
    lines = result.stdout.splitlines()
    assert len(lines) == 1, f"stdout must be one JSON object; got {result.stdout!r}, stderr {result.stderr!r}"
    return result.exit_code, json.loads(lines[0])


# --- the parameters -----------------------------------------------------------


def test_read_options_default_to_a_source_column_and_no_strict() -> None:
    options = ReadOptions.taken_from(
        {
            "format": None,
            "sheet": None,
            "table": None,
            "encoding": None,
            "sep": None,
            "header": True,
            "credentials": None,
            "as_text": False,
            "dtypes": None,
            "limit": None,
            "query": None,
            "source_column": "_source",
            "strict": False,
        }
    )
    assert (options.source_column, options.strict) == ("_source", False)


def test_a_chunk_of_no_rows_is_invalid(workdir: Path) -> None:
    with pytest.raises(DataioError) as caught:
        write(pd.DataFrame({"x": [1]}), "out.csv", chunk_rows=0)
    assert caught.value.code == "INVALID_ARGUMENTS"
    assert not (workdir / "out.csv").exists()


def test_the_new_flags_reach_the_library_from_convert(workdir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[ReadOptions, WriteOptions]] = []

    def claim(source: str, target: str, read_options: ReadOptions, write_options: WriteOptions) -> Report:
        seen.append((read_options, write_options))
        return Report()

    monkeypatch.setattr(batch, "converts_each", lambda source, target: True)
    monkeypatch.setattr(batch, "convert_each", claim)
    code, _ = invoke_json(
        "convert",
        "a.csv",
        "b.csv",
        "--source-column",
        "file",
        "--strict",
        "--split-by",
        "x",
        "--chunk-rows",
        "5",
        "--drop-split-column",
        "--keep-going",
    )
    assert code == 0
    read_options, write_options = seen[0]
    assert (read_options.source_column, read_options.strict) == ("file", True)
    assert (write_options.split_by, write_options.chunk_rows) == ("x", 5)
    assert (write_options.drop_split_column, write_options.keep_going) == (True, True)


# --- the batch report -----------------------------------------------------------


def test_a_batch_report_with_errors_is_ok_false_and_exit_1(workdir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    report = Report(
        targets=[BatchTarget(uri="out/a.xlsx", rows=2)],
        errors=[BatchError(uri="in/b.csv", code="READ_FAILED", message="Could not read 'in/b.csv': bad")],
    )
    monkeypatch.setattr(batch, "converts_each", lambda source, target: True)
    monkeypatch.setattr(batch, "convert_each", lambda *args: report)
    code, payload = invoke_json("convert", "in/*.csv", "out/{stem}.xlsx", "--keep-going")
    assert code == 1
    assert payload["ok"] is False
    assert payload["targets"] == [{"uri": "out/a.xlsx", "rows": 2}]
    assert payload["errors"] == [
        {"uri": "in/b.csv", "code": "READ_FAILED", "message": "Could not read 'in/b.csv': bad"}
    ]


def test_a_batch_report_without_errors_is_ok(workdir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    report = Report(targets=[BatchTarget(uri="out/a.xlsx", rows=2), BatchTarget(uri="out/b.xlsx", rows=5)])
    monkeypatch.setattr(batch, "converts_each", lambda source, target: True)
    monkeypatch.setattr(batch, "convert_each", lambda *args: report)
    code, payload = invoke_json("convert", "in/*.csv", "out/{stem}.xlsx")
    assert code == 0
    assert payload["ok"] is True
    assert payload["targets"] == [{"uri": "out/a.xlsx", "rows": 2}, {"uri": "out/b.xlsx", "rows": 5}]
    assert "errors" not in payload
    assert "target" not in payload


def test_a_dry_run_batch_lists_every_target_with_its_rows(workdir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    planned = PlannedBatchTarget(uri="out/a.xlsx", rows=2, exists=True, rows_before=7, rows_after=2)
    monkeypatch.setattr(batch, "converts_each", lambda source, target: True)
    monkeypatch.setattr(batch, "convert_each", lambda *args: Report(targets=[planned]))
    code, payload = invoke_json("convert", "in/*.csv", "out/{stem}.xlsx", "--dry-run")
    assert code == 0
    assert payload["targets"] == [{"uri": "out/a.xlsx", "rows": 2, "exists": True, "rows_before": 7, "rows_after": 2}]


def test_a_single_report_has_no_targets_and_no_errors(workdir: Path) -> None:
    code, payload = invoke_json("convert", "a.csv", "b.csv")
    assert code == 0
    assert "targets" not in payload
    assert "errors" not in payload


# --- SCHEMA_MISMATCH ------------------------------------------------------------


def test_schema_mismatch_names_each_source_with_its_columns() -> None:
    error = SchemaMismatch({"in/a.csv": ["a", "b"], "in/b.csv": ["a", "c"]})
    assert (error.code, error.exit_code) == ("SCHEMA_MISMATCH", 2)
    assert error.message == "The sources have different columns: in/a.csv (a, b); in/b.csv (a, c)."


def test_schema_mismatch_in_the_cli_is_exit_2(workdir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def mismatch(source: object, options: ReadOptions) -> None:
        raise SchemaMismatch({"in/a.csv": ["a", "b"], "in/b.csv": ["a", "c"]})

    monkeypatch.setattr(sources, "names_many", lambda source, options: True)
    monkeypatch.setattr(sources, "read_many", mismatch)
    code, payload = invoke_json("convert", "in/*.csv", "out.csv", "--strict")
    assert code == 2
    assert payload["ok"] is False
    assert payload["error"]["code"] == "SCHEMA_MISMATCH"
    assert "in/a.csv (a, b); in/b.csv (a, c)" in payload["error"]["message"]


# --- the seams ----------------------------------------------------------------


def test_read_asks_the_sources_module(monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list[object] = []
    merged = pd.DataFrame({"x": [1, 2]})
    part = SourcePart(uri="many", format="csv", encoding=None, delimiter=None, rows=2, columns=["x"])

    def names_many(source: object, options: ReadOptions) -> bool:
        asked.append(source)
        return source == "many"

    monkeypatch.setattr(sources, "names_many", names_many)
    monkeypatch.setattr(sources, "read_many", lambda source, options: (merged, part, ["union"]))
    assert read("many").equals(merged)
    assert asked == ["many"]


def test_write_asks_the_targets_module(monkeypatch: pytest.MonkeyPatch) -> None:
    report = Report(targets=[BatchTarget(uri="out/a.csv", rows=1)])
    monkeypatch.setattr(targets, "is_template", lambda target, options: target == "out/{x}.csv")
    monkeypatch.setattr(targets, "write_many", lambda frame, target, options: report)
    assert write(pd.DataFrame({"x": [1]}), "out/{x}.csv") == report


def test_convert_asks_the_batch_module(monkeypatch: pytest.MonkeyPatch) -> None:
    report = Report(targets=[BatchTarget(uri="out/a.xlsx", rows=1)])
    monkeypatch.setattr(
        batch, "converts_each", lambda source, target: (source, target) == ("in/*.csv", "out/{stem}.xlsx")
    )
    monkeypatch.setattr(batch, "convert_each", lambda source, target, read_options, write_options: report)
    assert convert("in/*.csv", "out/{stem}.xlsx") == report


def test_unpatched_the_modules_claim_nothing(workdir: Path) -> None:
    report = convert("a.csv", "b.csv")
    assert report.target is not None
    assert report.targets is None
    assert read("a.csv").to_dict("records") == [{"x": 1, "y": 2}, {"x": 3, "y": 4}]
    assert rb_dataio.write(read("a.csv"), "c.csv").target is not None
