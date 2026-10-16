"""Remote sources in the core, through the public library API and the CLI under --json.

The formats are fakes of this file: `FakeSheets`, a remote container that claims gsheet
addresses and keeps its spreadsheets in memory, and `FakeHttp`, a scheme adapter that
claims https and answers from a dict of pages. They replace any real format of their
schemes in the registry. No test uses the network.
"""

from __future__ import annotations

import io
import json
from collections.abc import Callable
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from rb_dataio import DataioError, backups, info, read, restore, write
from rb_dataio.cli import app
from rb_dataio.core.dataio import registry
from rb_dataio.core.dataio.address import Address
from rb_dataio.core.dataio.options import ReadOptions, WriteOptions
from rb_dataio.formats import FormatAdapter, Loaded, Remote, RemoteAdapter, RemoteContainerAdapter

URL = "https://docs.google.com/spreadsheets/d/ID/edit#gid=123"
PAGE = "https://example.com/export/phrases.csv"
PUBLISHED = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT/pub?output=csv"
NEW = pd.DataFrame({"phrase": ["ёлка", "шар", "гирлянда"]})
runner = CliRunner()


def sheet(*values: str) -> pd.DataFrame:
    return pd.DataFrame({"phrase": list(values)})


class FakeSheets(RemoteContainerAdapter):
    """Spreadsheets by id; each has sheets by title with a gid. `written` records each write."""

    name = "fakesheets"
    schemes = ("gsheet",)
    options = ("sheet", "start", "value_input", "credentials")
    first_part = "Sheet1"
    confirms_replace = True

    def __init__(self) -> None:
        self.books: dict[str, dict[str, tuple[int, pd.DataFrame]]] = {
            "ID": {"Sheet1": (0, sheet("купить ёлку", "ёлка цена")), "Data": (123, sheet("шар"))}
        }
        self.written: list[tuple[Remote, str, WriteOptions]] = []

    def parts(self, location: Remote) -> list[str]:
        return list(self.books[location.address.path])

    def part_named(self, location: Remote) -> str | None:
        book = self.books[location.address.path]
        by_gid = {gid: title for title, (gid, _) in book.items()}
        return by_gid[location.address.gid] if location.address.gid is not None else location.address.fragment

    def read_part(self, location: Remote, part: str, options: ReadOptions) -> Loaded:
        return Loaded(self.books[location.address.path][part][1].copy())

    def write_part(self, frame: pd.DataFrame, location: Remote, part: str, options: WriteOptions) -> list[str]:
        book = self.books[location.address.path]
        gid = book[part][0] if part in book else max(gid for gid, _ in book.values()) + 1
        book[part] = (gid, frame.copy())
        self.written.append((location, part, options))
        return []

    def rows(self, part: str) -> list[str]:
        return self.books["ID"][part][1]["phrase"].tolist()


class FakeHttp(RemoteAdapter):
    """CSV pages by their URL."""

    name = "fakehttp"
    schemes = ("https",)
    options = ()

    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages

    def read_address(self, address: Address, options: ReadOptions) -> Loaded:
        return Loaded(pd.read_csv(io.StringIO(self.pages[address.text]), dtype=str))


@pytest.fixture
def known(monkeypatch: pytest.MonkeyPatch) -> Callable[..., None]:
    """Make these adapters the formats of their schemes, in place of any real format of the same schemes."""
    real = registry.adapters()

    def use(*fakes: FormatAdapter) -> None:
        schemes = {scheme for fake in fakes for scheme in fake.schemes}
        kept = [adapter for adapter in real if not schemes & set(adapter.schemes)]
        monkeypatch.setattr(registry, "adapters", lambda: [*kept, *fakes])

    return use


@pytest.fixture
def sheets(known: Callable[..., None], data_dir: Path) -> FakeSheets:
    fake = FakeSheets()
    known(fake)
    return fake


def invoke_json(*args: str) -> tuple[int, dict]:
    result = runner.invoke(app, [*args, "--json"])
    return result.exit_code, json.loads(result.stdout)


@pytest.fixture
def source_csv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """new.csv in the current directory: the 3 rows of NEW."""
    monkeypatch.chdir(tmp_path)
    NEW.to_csv(tmp_path / "new.csv", index=False)
    return "new.csv"


# --- addresses --------------------------------------------------------------------


def test_a_google_sheets_url_names_the_spreadsheet_and_the_sheet_by_gid(sheets: FakeSheets) -> None:
    assert read(URL)["phrase"].tolist() == ["шар"]


def test_a_gsheet_address_names_the_sheet_after_the_hash(sheets: FakeSheets) -> None:
    assert read("gsheet://ID#Sheet1")["phrase"].tolist() == ["купить ёлку", "ёлка цена"]


def test_the_sheet_parameter_wins_over_the_gid(sheets: FakeSheets) -> None:
    assert read(URL, sheet="Sheet1")["phrase"].tolist() == ["купить ёлку", "ёлка цена"]


def test_a_google_sheets_url_without_gid_reads_the_first_sheet(sheets: FakeSheets) -> None:
    assert read("https://docs.google.com/spreadsheets/d/ID/edit")["phrase"].tolist() == ["купить ёлку", "ёлка цена"]


def test_info_lists_the_sheets(sheets: FakeSheets) -> None:
    assert info("gsheet://ID").parts == ["Sheet1", "Data"]


# --- scheme adapters --------------------------------------------------------------


def test_an_https_url_is_read_by_the_adapter_that_claims_https(known: Callable[..., None]) -> None:
    known(FakeHttp({PAGE: "phrase,freq\nёлка,7\n", PUBLISHED: "phrase\nшар\n"}))
    assert read(PAGE).to_dict("list") == {"phrase": ["ёлка"], "freq": [7]}
    assert read(PUBLISHED).to_dict("list") == {"phrase": ["шар"]}  # a 'Publish to web' link is no spreadsheet


def test_a_scheme_no_adapter_claims_is_format_unsupported(known: Callable[..., None]) -> None:
    known(FakeHttp({}))
    with pytest.raises(DataioError) as caught:
        read("s3://bucket/phrases.csv")
    assert (caught.value.code, caught.value.exit_code) == ("FORMAT_UNSUPPORTED", 2)
    with pytest.raises(DataioError) as writing:
        write(NEW, PAGE)
    assert writing.value.code == "FORMAT_UNSUPPORTED"


# --- the confirmation of a replace of a non-empty part ------------------------------


def test_the_library_needs_overwrite_to_replace_a_non_empty_part(sheets: FakeSheets) -> None:
    with pytest.raises(DataioError) as caught:
        write(NEW, "gsheet://ID#Sheet1")
    assert (caught.value.code, caught.value.exit_code) == ("TARGET_EXISTS", 1)
    assert caught.value.action == "Pass overwrite=True / --confirm to replace it; a backup is kept."
    assert sheets.rows("Sheet1") == ["купить ёлку", "ёлка цена"]

    write(NEW, "gsheet://ID#Sheet1", overwrite=True)
    assert sheets.rows("Sheet1") == ["ёлка", "шар", "гирлянда"]


def test_a_new_part_needs_no_confirmation(sheets: FakeSheets) -> None:
    report = write(NEW, "gsheet://ID#New")
    assert (report.target.uri, report.target.rows) == ("gsheet://ID#New", 3)
    assert sheets.rows("New") == ["ёлка", "шар", "гирлянда"]
    assert backups() == []


def test_mode_error_refuses_an_existing_part(sheets: FakeSheets) -> None:
    with pytest.raises(DataioError) as caught:
        write(NEW, "gsheet://ID#Data", mode="error")
    assert caught.value.code == "TARGET_EXISTS"
    write(NEW, "gsheet://ID#Other", mode="error")
    assert sheets.rows("Other") == ["ёлка", "шар", "гирлянда"]


def test_the_cli_refuses_the_replace_under_non_interactive_without_confirm(sheets: FakeSheets, source_csv: str) -> None:
    code, payload = invoke_json("--non-interactive", "convert", source_csv, "gsheet://ID#Sheet1")
    assert (code, payload["error"]["code"]) == (2, "INVALID_ARGUMENTS")
    assert "--confirm" in payload["error"]["message"]
    assert sheets.rows("Sheet1") == ["купить ёлку", "ёлка цена"]


def test_the_cli_replaces_with_confirm_and_keeps_a_backup(sheets: FakeSheets, source_csv: str) -> None:
    code, payload = invoke_json("--non-interactive", "convert", source_csv, "gsheet://ID#Sheet1", "--confirm")
    assert (code, payload["target"]["rows"]) == (0, 3)
    assert sheets.rows("Sheet1") == ["ёлка", "шар", "гирлянда"]

    kept = backups()
    assert [(entry.target, entry.table, entry.rows) for entry in kept] == [("gsheet://ID", "Sheet1", 2)]
    restore(kept[0].id)
    assert sheets.rows("Sheet1") == ["купить ёлку", "ёлка цена"]


def test_a_replace_of_a_sheet_with_no_columns_succeeds_and_keeps_no_backup(sheets: FakeSheets) -> None:
    sheets.books["ID"]["Empty"] = (7, pd.DataFrame())
    write(NEW, "gsheet://ID#Empty", overwrite=True)
    assert sheets.rows("Empty") == ["ёлка", "шар", "гирлянда"]
    assert backups() == []


def test_a_replace_of_a_sheet_with_one_row_keeps_a_backup(sheets: FakeSheets) -> None:
    write(NEW, "gsheet://ID#Data", overwrite=True)
    assert [(entry.table, entry.rows) for entry in backups()] == [("Data", 1)]


def test_the_cli_dry_run_shows_the_rows_before_and_after_and_changes_nothing(
    sheets: FakeSheets, source_csv: str
) -> None:
    code, payload = invoke_json("--non-interactive", "convert", source_csv, "gsheet://ID#Sheet1", "--dry-run")
    assert code == 0
    target = payload["target"]
    assert (target["exists"], target["rows_before"], target["rows_after"]) == (True, 2, 3)
    assert sheets.rows("Sheet1") == ["купить ёлку", "ёлка цена"]
    assert sheets.written == []


# --- start, value_input and credentials reach the format ---------------------------


def test_start_value_input_and_credentials_reach_the_format(sheets: FakeSheets) -> None:
    write(NEW, "gsheet://ID#New", start="A5", value_input="user", credentials="key.json")
    location, part, options = sheets.written[-1]
    assert (part, options.start, options.value_input, location.credentials) == ("New", "A5", "user", "key.json")


def test_value_input_is_raw_by_default(sheets: FakeSheets) -> None:
    write(NEW, "gsheet://ID#New")
    _, _, options = sheets.written[-1]
    assert (options.start, options.value_input) == (None, "raw")


def test_an_unknown_value_input_is_invalid_arguments(sheets: FakeSheets) -> None:
    with pytest.raises(DataioError) as caught:
        write(NEW, "gsheet://ID#New", value_input="formula")
    assert caught.value.code == "INVALID_ARGUMENTS"
    assert caught.value.message == "value_input must be one of raw, user, not 'formula'."


def test_the_cli_flags_reach_the_format(sheets: FakeSheets, source_csv: str) -> None:
    args = ["--start", "B2", "--value-input", "user", "--out-credentials", "key.json"]
    code, _ = invoke_json("convert", source_csv, "gsheet://ID#New", *args)
    assert code == 0
    location, _, options = sheets.written[-1]
    assert (options.start, options.value_input, location.credentials) == ("B2", "user", "key.json")
