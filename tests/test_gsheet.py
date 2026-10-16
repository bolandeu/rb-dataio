"""Google Sheets, through the public library API and the CLI under --json.

The gspread client is a fake of this file (`FakeClient`): its spreadsheets keep their cells
in memory, every call is recorded, and a call can be made to fail once. The key comes from
the env vars DATAIO_GOOGLE_*; the sleep of a backoff is recorded, not slept. No test uses
the network.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
import requests
from gspread.exceptions import APIError, SpreadsheetNotFound
from gspread.utils import a1_to_rowcol
from typer.testing import CliRunner

from rb_dataio import DataioError, backups, read, restore, write
from rb_dataio.cli import app
from rb_dataio.core.errors import ProviderError
from rb_dataio.providers import google

EMAIL = "robot@demo.iam.gserviceaccount.com"
URL = "https://docs.google.com/spreadsheets/d/ID/edit#gid=123"
SHEET1 = [["phrase", "freq"], ["купить ёлку", 7], ["ёлка цена", 3]]
DATA = [["phrase"], ["шар"]]
NEW = pd.DataFrame({"phrase": ["ёлка", "шар", "гирлянда"]})
WRITE_CALLS = {"update", "clear", "resize", "add_worksheet"}
runner = CliRunner()


def api_error(status: int) -> APIError:
    """The error gspread raises for an HTTP status of the Sheets API."""
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps({"error": {"code": status, "message": f"status {status}"}}).encode()
    return APIError(response)


def unshared() -> PermissionError:
    """What gspread raises when the spreadsheet is not shared with the service account (a 403)."""
    error = PermissionError()
    error.__cause__ = api_error(403)
    return error


def missing() -> SpreadsheetNotFound:
    """What gspread raises for a spreadsheet id that has no spreadsheet (a 404)."""
    error = SpreadsheetNotFound(api_error(404).response)
    error.__cause__ = api_error(404)
    return error


class FakeSheet:
    """A worksheet: its cells by (row, column) from 1 in a grid of `row_count` x `col_count`, as Google has it."""

    def __init__(self, client: FakeClient, title: str, gid: int, rows: int = 1000, cols: int = 26) -> None:
        self.client, self.title, self.id = client, title, gid
        self.row_count, self.col_count = rows, cols
        self.cells: dict[tuple[int, int], Any] = {}

    def values(self) -> list[list[Any]]:
        """The cells from A1 to the last one with a value, empty ones as ''."""
        if not self.cells:
            return []
        height = max(row for row, _ in self.cells)
        width = max(column for _, column in self.cells)
        return [[self.cells.get((row, column), "") for column in range(1, width + 1)] for row in range(1, height + 1)]

    def cell(self, label: str) -> Any:
        return self.cells.get(a1_to_rowcol(label), "")

    def get_values(self, **options: Any) -> list[list[Any]]:
        self.client.called("get_values", self.title, options)
        return self.values()

    def update(self, values: list[list[Any]], range_name: str, value_input_option: str) -> None:
        self.client.called("update", self.title, (len(values), range_name, value_input_option))
        top, left = a1_to_rowcol(range_name)
        if top - 1 + len(values) > self.row_count or left - 1 + max(map(len, values)) > self.col_count:
            raise api_error(400)  # Google: the range exceeds the grid limits
        for row, line in enumerate(values, start=top):
            for column, value in enumerate(line, start=left):
                self.cells[(row, column)] = value

    def clear(self) -> None:
        self.client.called("clear", self.title)
        self.cells = {}

    def resize(self, rows: int, cols: int) -> None:
        self.client.called("resize", self.title, (rows, cols))
        self.row_count, self.col_count = rows, cols


class FakeSpreadsheet:
    def __init__(self, client: FakeClient) -> None:
        self.client = client
        self.sheets: list[FakeSheet] = []

    def sheet(self, title: str) -> FakeSheet:
        return next(sheet for sheet in self.sheets if sheet.title == title)

    def with_sheet(self, title: str, gid: int, rows: list[list[Any]]) -> FakeSpreadsheet:
        sheet = FakeSheet(self.client, title, gid)
        sheet.cells = {(row, column): value for row, line in enumerate(rows, 1) for column, value in enumerate(line, 1)}
        self.sheets.append(sheet)
        return self

    def worksheets(self) -> list[FakeSheet]:
        self.client.called("worksheets", "")
        return list(self.sheets)

    def add_worksheet(self, title: str, rows: int, cols: int) -> FakeSheet:
        self.client.called("add_worksheet", title, (rows, cols))
        sheet = FakeSheet(self.client, title, max(sheet.id for sheet in self.sheets) + 1, rows, cols)
        self.sheets.append(sheet)
        return sheet


class FakeClient:
    """Spreadsheets by id. `calls` records every call (name, sheet, details); `fail` makes the next call fail."""

    def __init__(self) -> None:
        self.spreadsheets = {"ID": FakeSpreadsheet(self).with_sheet("Sheet1", 0, SHEET1).with_sheet("Data", 123, DATA)}
        self.calls: list[tuple[str, str, Any]] = []
        self.failures: dict[str, list[Exception]] = defaultdict(list)

    def fail(self, call: str, *errors: Exception) -> None:
        self.failures[call].extend(errors)

    def called(self, call: str, sheet: str, details: Any = None) -> None:
        self.calls.append((call, sheet, details))
        if self.failures[call]:
            raise self.failures[call].pop(0)

    def open_by_key(self, key: str) -> FakeSpreadsheet:
        self.called("open_by_key", "")
        return self.spreadsheets[key]

    def sheet(self, title: str) -> FakeSheet:
        return self.spreadsheets["ID"].sheet(title)

    def names(self) -> set[str]:
        return {call for call, _, _ in self.calls}

    def updates(self) -> list[Any]:
        return [details for call, _, details in self.calls if call == "update"]


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, fake_keyring: dict, data_dir: Path) -> FakeClient:
    """The fake client, given for the key of the env; the user data dir (backups) in a temporary folder."""
    monkeypatch.setenv("DATAIO_GOOGLE_CLIENT_EMAIL", EMAIL)
    monkeypatch.setenv("DATAIO_GOOGLE_PRIVATE_KEY", "key")
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    fake = FakeClient()
    monkeypatch.setattr(google, "connect", lambda account: fake)
    return fake


@pytest.fixture
def delays(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """The seconds of each backoff: recorded, not slept."""
    slept: list[float] = []
    monkeypatch.setattr(google.time, "sleep", slept.append)
    return slept


def invoke_json(*args: str) -> tuple[int, dict]:
    result = runner.invoke(app, [*args, "--json"])
    return result.exit_code, json.loads(result.stdout)


# --- the sheet of an address ----------------------------------------------------------


def test_a_browser_url_reads_the_sheet_of_its_gid(client: FakeClient) -> None:
    assert read(URL).to_dict("list") == {"phrase": ["шар"]}


def test_a_gsheet_address_reads_the_sheet_after_the_hash(client: FakeClient) -> None:
    assert read("gsheet://ID#Sheet1").to_dict("list") == {"phrase": ["купить ёлку", "ёлка цена"], "freq": [7, 3]}


def test_a_gid_the_spreadsheet_lacks_lists_its_sheets(client: FakeClient) -> None:
    with pytest.raises(DataioError) as caught:
        read("https://docs.google.com/spreadsheets/d/ID/edit#gid=9")
    assert (caught.value.code, caught.value.action) == ("SOURCE_NOT_FOUND", "Name one of the parts: Sheet1, Data.")


def test_the_cli_reads_a_sheet_into_a_file(client: FakeClient, tmp_path: Path) -> None:
    code, _ = invoke_json("convert", "gsheet://ID#Data", str(tmp_path / "out.csv"))
    assert code == 0
    assert (tmp_path / "out.csv").read_text(encoding="utf-8") == "phrase\nшар\n"


# --- access ----------------------------------------------------------------------------


def test_an_unshared_sheet_says_whom_to_share_it_with(client: FakeClient) -> None:
    client.fail("open_by_key", unshared(), unshared())
    for attempt in (lambda: read("gsheet://ID#Sheet1"), lambda: write(NEW, "gsheet://ID#New")):
        with pytest.raises(DataioError) as caught:
            attempt()
        assert (caught.value.code, caught.value.exit_code) == ("AUTH_REQUIRED", 3)
        assert caught.value.action == f"Share the sheet with {EMAIL} as Editor."


def test_a_403_on_write_says_whom_to_share_it_with_too(client: FakeClient) -> None:
    client.fail("add_worksheet", api_error(403))  # shared as Viewer: it reads but does not write
    with pytest.raises(DataioError) as caught:
        write(NEW, "gsheet://ID#New")
    assert caught.value.action == f"Share the sheet with {EMAIL} as Editor."


def test_the_cli_reports_an_unshared_sheet_with_exit_3(client: FakeClient) -> None:
    client.fail("open_by_key", unshared())
    code, payload = invoke_json("convert", "gsheet://ID#Sheet1", "-")
    assert (code, payload["error"]["code"]) == (3, "AUTH_REQUIRED")
    assert payload["error"]["action"] == f"Share the sheet with {EMAIL} as Editor."


def test_a_spreadsheet_that_is_not_there_is_a_provider_error(client: FakeClient) -> None:
    client.fail("open_by_key", missing())
    with pytest.raises(ProviderError) as caught:
        read("gsheet://ID#Sheet1")
    assert (caught.value.code, caught.value.exit_code, caught.value.status) == ("PROVIDER_ERROR", 5, 404)


# --- a new sheet and start --------------------------------------------------------------


def test_a_missing_sheet_is_created(client: FakeClient) -> None:
    write(NEW, "gsheet://ID#New")
    assert client.sheet("New").values() == [["phrase"], ["ёлка"], ["шар"], ["гирлянда"]]
    assert [sheet.title for sheet in client.spreadsheets["ID"].sheets] == ["Sheet1", "Data", "New"]


def test_start_places_the_header(client: FakeClient) -> None:
    write(NEW, "gsheet://ID#New", start="A5")
    new = client.sheet("New")
    assert (new.cell("A4"), new.cell("A5"), new.cell("A6"), new.cell("A8")) == ("", "phrase", "ёлка", "гирлянда")


def test_a_start_that_is_no_cell_is_invalid_arguments(client: FakeClient) -> None:
    with pytest.raises(DataioError) as caught:
        write(NEW, "gsheet://ID#New", start="top")
    assert (caught.value.code, caught.value.message) == (
        "INVALID_ARGUMENTS",
        "start must be a cell such as A5, not 'top'.",
    )
    assert not client.names() & WRITE_CALLS


def test_a_sheet_too_small_for_the_table_is_grown(client: FakeClient) -> None:
    write(pd.DataFrame({"n": range(1500)}), "gsheet://ID#Data", start="C1", overwrite=True)
    data = client.sheet("Data")
    assert (data.cell("C1"), data.cell("C1501"), data.row_count) == ("n", 1499, 1501)


# --- values -----------------------------------------------------------------------------


def test_values_are_written_raw(client: FakeClient) -> None:
    write(pd.DataFrame({"code": ["007", "=1+1"]}), "gsheet://ID#New")
    assert client.updates() == [(3, "A1", "RAW")]
    assert client.sheet("New").values() == [["code"], ["007"], ["=1+1"]]


def test_value_input_user_lets_google_parse_them(client: FakeClient) -> None:
    write(pd.DataFrame({"code": ["007", "=1+1"]}), "gsheet://ID#New", value_input="user")
    assert client.updates() == [(3, "A1", "USER_ENTERED")]


def test_numbers_dates_and_missing_values_are_written_as_cells(client: FakeClient) -> None:
    frame = pd.DataFrame({"n": [1, None], "day": pd.to_datetime(["2026-10-16", None])})
    write(frame, "gsheet://ID#New")
    assert client.sheet("New").values() == [["n", "day"], [1.0, "2026-10-16T00:00:00"], ["", ""]]


# --- replace, backup and restore -----------------------------------------------------------


def test_a_confirmed_replace_keeps_a_backup_and_clears_only_values(client: FakeClient) -> None:
    write(NEW, "gsheet://ID#Sheet1", overwrite=True)
    assert client.sheet("Sheet1").values() == [["phrase"], ["ёлка"], ["шар"], ["гирлянда"]]
    assert "clear" in client.names()
    assert client.names() <= {"open_by_key", "worksheets", "get_values", "clear", "update"}  # no format call

    [kept] = backups()
    assert (kept.target, kept.table, kept.rows, kept.columns) == ("gsheet://ID", "Sheet1", 2, ["phrase", "freq"])
    restore(kept.id)
    assert client.sheet("Sheet1").values() == SHEET1


def test_a_replace_without_overwrite_is_refused(client: FakeClient) -> None:
    with pytest.raises(DataioError) as caught:
        write(NEW, "gsheet://ID#Sheet1")
    assert caught.value.code == "TARGET_EXISTS"
    assert client.sheet("Sheet1").values() == SHEET1


def test_the_cli_replaces_with_confirm(client: FakeClient, tmp_path: Path) -> None:
    NEW.to_csv(tmp_path / "new.csv", index=False)
    code, payload = invoke_json("--non-interactive", "convert", str(tmp_path / "new.csv"), URL, "--confirm")
    assert (code, payload["target"]["rows"]) == (0, 3)
    assert client.sheet("Data").values() == [["phrase"], ["ёлка"], ["шар"], ["гирлянда"]]


# --- modes --------------------------------------------------------------------------------


def test_append_adds_rows_below_the_table(client: FakeClient) -> None:
    write(pd.DataFrame({"phrase": ["ель"], "freq": [1]}), "gsheet://ID#Sheet1", mode="append")
    assert client.sheet("Sheet1").values() == [*SHEET1, ["ель", 1]]
    assert backups() == []


def test_append_with_another_header_is_refused(client: FakeClient) -> None:
    with pytest.raises(DataioError) as caught:
        write(pd.DataFrame({"word": ["ель"]}), "gsheet://ID#Sheet1", mode="append")
    assert caught.value.code == "WRITE_FAILED"
    assert client.sheet("Sheet1").values() == SHEET1


def test_append_to_a_new_sheet_writes_the_header(client: FakeClient) -> None:
    write(NEW, "gsheet://ID#New", mode="append")
    assert client.sheet("New").values() == [["phrase"], ["ёлка"], ["шар"], ["гирлянда"]]


def test_mode_error_refuses_an_existing_sheet(client: FakeClient) -> None:
    with pytest.raises(DataioError) as caught:
        write(NEW, "gsheet://ID#Data", mode="error")
    assert caught.value.code == "TARGET_EXISTS"
    assert client.sheet("Data").values() == DATA


# --- batches, backoff and the cell limit -------------------------------------------------


def test_rows_go_in_batches_of_10_000(client: FakeClient) -> None:
    write(pd.DataFrame({"n": range(25_000)}), "gsheet://ID#New")
    # the header rides with the first batch: 1 + 10 000 rows
    assert client.updates() == [(10_001, "A1", "RAW"), (10_000, "A10002", "RAW"), (5_000, "A20002", "RAW")]
    new = client.sheet("New")
    assert (new.cell("A2"), new.cell("A25001"), new.cell("A25002")) == (0, 24_999, "")


def test_a_429_is_retried_after_a_backoff(client: FakeClient, delays: list[float]) -> None:
    client.fail("update", api_error(429))
    write(NEW, "gsheet://ID#New")
    assert client.updates() == [(4, "A1", "RAW"), (4, "A1", "RAW")]
    assert len(delays) == 1 and delays[0] > 0
    assert client.sheet("New").values() == [["phrase"], ["ёлка"], ["шар"], ["гирлянда"]]


def test_a_5xx_that_lasts_is_a_provider_error_after_growing_backoffs(client: FakeClient, delays: list[float]) -> None:
    client.fail("update", *(api_error(503) for _ in range(100)))
    with pytest.raises(ProviderError) as caught:
        write(NEW, "gsheet://ID#New")
    assert (caught.value.code, caught.value.exit_code, caught.value.status) == ("PROVIDER_ERROR", 5, 503)
    assert len(delays) >= 2 and delays == sorted(delays) and delays[0] < delays[-1]
    assert len(client.updates()) == len(delays) + 1


def test_more_than_10_million_cells_is_refused_before_any_write(client: FakeClient) -> None:
    wide = pd.DataFrame(np.zeros((1_000, 10_001), dtype=np.int8))  # 10 001 000 cells
    with pytest.raises(DataioError) as caught:
        write(wide, "gsheet://ID#New")
    assert caught.value.code == "WRITE_FAILED"
    assert not client.names() & WRITE_CALLS


# --- formats -----------------------------------------------------------------------------


def test_formats_lists_gsheet_with_read_write_and_append() -> None:
    code, payload = invoke_json("formats")
    [entry] = [entry for entry in payload["formats"] if entry["name"] == "gsheet"]
    assert (code, entry["read"], entry["write"], entry["append"]) == (0, True, True, True)
    assert {"start", "value_input", "credentials"} <= set(entry["options"])
