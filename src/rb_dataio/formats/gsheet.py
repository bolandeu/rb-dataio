"""Google Sheets: a spreadsheet is a container whose parts are its sheets, through gspread (ADR 0002).

The address is `gsheet://<id>#<sheet>` or a browser URL whose `gid` names the sheet (core/dataio/address.py).
Every request goes through the google provider (providers/google.py): its key, its backoff on 429 and
5xx, and a 403 that names the email to share the sheet with. A read takes the cells as Google holds
them (a number a number, a date its text) from the first row and the first column with a value; an
empty cell is missing. A write puts values only, never a format: `value_input` raw (`007` and `=1+1`
stay text) or user (Google parses them as if typed), the top-left cell of the table at `start` (A1),
in batches of rows (data/settings.toml), on a sheet grown to fit it. A replace clears the old values
and keeps the formatting; an append puts the rows below the table after a check of its header; a
missing sheet is added. A table of more cells than a spreadsheet holds is refused before any request.
"""

from __future__ import annotations

import datetime as dt
import functools
from collections.abc import Callable
from typing import Any, TypeVar

import pandas as pd
from gspread.exceptions import IncorrectCellLabel
from gspread.utils import DateTimeOption, ValueInputOption, ValueRenderOption, a1_to_rowcol, rowcol_to_a1
from gspread.worksheet import Worksheet

from ..core.dataio.address import GOOGLE_SHEETS
from ..core.dataio.options import Mode, ReadOptions, ValueInput, WriteOptions
from ..core.dataio.report import column_names
from ..core.dataio.settings import settings
from ..core.errors import InvalidParameter, PartNotFound
from ..providers.google import GoogleProvider
from . import EMPTY_CELL, Loaded, Remote, RemoteContainerAdapter, WriteRefused, from_cells
from .csv import require_same_header
from .json import plain

TOP_LEFT = "A1"  # where a table goes with no `start`
VALUE_INPUTS = {ValueInput.RAW: ValueInputOption.raw, ValueInput.USER: ValueInputOption.user_entered}
Answer = TypeVar("Answer")
Cells = list[list[Any]]


class _Spreadsheet:
    """The spreadsheet of a remote location; every request to it goes through the google provider."""

    def __init__(self, location: Remote) -> None:
        self.uri = location.address.text
        self.provider = GoogleProvider(key_file=location.credentials)
        client = self.provider.sheets()
        self.book = self.call(lambda: client.open_by_key(location.address.path))

    def call(self, request: Callable[[], Answer]) -> Answer:
        return self.provider.call(request, self.uri)

    def sheets(self) -> list[Worksheet]:
        return self.call(self.book.worksheets)

    def sheet(self, title: str) -> Worksheet | None:
        return next((sheet for sheet in self.sheets() if sheet.title == title), None)

    def values(self, sheet: Worksheet) -> Cells:
        """The cells of `sheet` from A1, as Google holds them: a number a number, a date its text, an empty one ''."""
        return self.call(
            lambda: sheet.get_values(
                value_render_option=ValueRenderOption.unformatted,
                date_time_render_option=DateTimeOption.formatted_string,
            )
        )


def _corner(values: Cells) -> tuple[int, int] | None:
    """The row and the column (from 1) where the cells with values start; None when no cell has one."""
    filled = [number for number, row in enumerate(values) if any(cell != EMPTY_CELL for cell in row)]
    if not filled:
        return None
    column = min(next(n for n, cell in enumerate(values[number]) if cell != EMPTY_CELL) for number in filled)
    return filled[0] + 1, column + 1


def _used(values: Cells) -> Cells:
    """The cells from the first row and the first column with a value: the table of the sheet."""
    corner = _corner(values)
    return [] if corner is None else [row[corner[1] - 1 :] for row in values[corner[0] - 1 :]]


def _header(values: Cells) -> list[str]:
    names = [str(cell) for cell in _used(values)[0]]
    while names and names[-1] == EMPTY_CELL:
        names.pop()
    return names


def _cell(value: Any) -> Any:
    """A value as the Sheets API takes it: a date its ISO text, a missing value an empty cell."""
    if value is None:
        return EMPTY_CELL
    return value.isoformat() if isinstance(value, dt.date) else value


def _rows(frame: pd.DataFrame) -> Cells:
    return [[_cell(value) for value in row] for row in plain(frame).itertuples(index=False, name=None)]


def _cell_at(label: str) -> tuple[int, int]:
    """The row and the column (from 1) of a cell label such as A5; another text is INVALID_ARGUMENTS."""
    try:
        return a1_to_rowcol(label)
    except IncorrectCellLabel:
        raise InvalidParameter(f"start must be a cell such as A5, not '{label}'.") from None


def _require_room(frame: pd.DataFrame, header: bool) -> None:
    cells = (len(frame) + int(header)) * len(frame.columns)
    limit = settings().gsheet.max_cells
    if cells > limit:
        raise WriteRefused(
            f"the table has {cells:,} cells, over the {limit:,} cells a Google spreadsheet holds.",
            action="Write csv or parquet, which have no cell limit, or fewer rows or columns.",
        )


def _batches(header: Cells, rows: Cells) -> list[Cells]:
    """The rows in batches of the settings' size; the header goes with the first."""
    size = settings().gsheet.batch_rows
    batches = [rows[first : first + size] for first in range(0, len(rows), size)] or [[]]
    batches[0] = [*header, *batches[0]]
    return batches


class GsheetAdapter(RemoteContainerAdapter):
    name = "gsheet"
    schemes = (GOOGLE_SHEETS,)
    options = ("sheet", "header", "start", "value_input", "credentials")
    appends = True
    first_part = "Sheet1"
    confirms_replace = True

    def part_named(self, location: Remote) -> str | None:
        """The sheet of the URL's gid, else the one after `#`; a gid of no sheet is SOURCE_NOT_FOUND."""
        gid = location.address.gid
        if gid is None:
            return location.address.fragment
        sheets = _Spreadsheet(location).sheets()
        titles = {sheet.id: sheet.title for sheet in sheets}
        if gid not in titles:
            raise PartNotFound(location.address.text, f"gid={gid}", list(titles.values()))
        return titles[gid]

    def parts(self, location: Remote) -> list[str]:
        return [sheet.title for sheet in _Spreadsheet(location).sheets()]

    def read_part(self, location: Remote, part: str, options: ReadOptions) -> Loaded:
        spreadsheet = _Spreadsheet(location)
        sheet = spreadsheet.sheet(part)
        return from_cells(_used(spreadsheet.values(sheet)) if sheet else [], options.header)

    def write_part(self, frame: pd.DataFrame, location: Remote, part: str, options: WriteOptions) -> list[str]:
        _require_room(frame, options.header)
        top, left = _cell_at(options.start or TOP_LEFT)
        spreadsheet = _Spreadsheet(location)
        sheet = spreadsheet.sheet(part)
        old = spreadsheet.values(sheet) if sheet else []
        header = [column_names(frame)] if options.header else []
        corner = _corner(old)
        if options.mode is Mode.APPEND and corner:
            if options.header:
                require_same_header(_header(old), frame)
            header, top, left = [], len(old) + 1, corner[1]
        batches = _batches(header, _rows(frame))
        rows = top - 1 + sum(map(len, batches))
        columns = left - 1 + max(len(frame.columns), 1)
        if sheet is None:
            sheet = spreadsheet.call(lambda: spreadsheet.book.add_worksheet(part, rows=rows, cols=columns))
        else:
            self._make_room(spreadsheet, sheet, old, rows, columns, options.mode)
        value_input = VALUE_INPUTS[options.value_input]
        for batch in batches:
            if batch:
                at = rowcol_to_a1(top, left)
                spreadsheet.call(functools.partial(sheet.update, batch, range_name=at, value_input_option=value_input))
            top += len(batch)
        return []

    @staticmethod
    def _make_room(
        spreadsheet: _Spreadsheet, sheet: Worksheet, old: Cells, rows: int, columns: int, mode: Mode
    ) -> None:
        """Clear the old values for a replace (the formatting stays) and grow the sheet to `rows` x `columns`."""
        if old and mode is not Mode.APPEND:
            spreadsheet.call(sheet.clear)
        if rows > sheet.row_count or columns > sheet.col_count:
            grown = (max(rows, sheet.row_count), max(columns, sheet.col_count))
            spreadsheet.call(lambda: sheet.resize(rows=grown[0], cols=grown[1]))


ADAPTER = GsheetAdapter()
