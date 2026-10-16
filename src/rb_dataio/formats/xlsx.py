"""xlsx: the Excel book dataio reads (_excel.py) and writes, one sheet at a time, through openpyxl.

A write loads the book, replaces its sheet in place (or adds it) and keeps the others; an
append adds the rows below the sheet's after a check of the header (an empty sheet gets
the header too). Every written sheet gets a frozen header row, an autofilter and columns
as wide as their longest value plus the padding of the settings (data/settings.toml).
A sheet over `MAX_ROWS` is refused before the write. openpyxl does not keep every part of
a book: a book with charts or pivot tables warns that they may be lost. Values only, no
formulas.
"""

from __future__ import annotations

import zipfile
from collections.abc import Iterable
from pathlib import Path

import openpyxl
import pandas as pd
from openpyxl.cell import Cell
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from ..core.dataio.options import Mode, WriteOptions
from ..core.dataio.report import column_names
from ..core.dataio.settings import settings
from . import WriteRefused
from ._excel import ExcelAdapter, book_errors
from .csv import require_same_header
from .json import plain

MAX_ROWS = 1_048_576  # the rows of an Excel sheet, the header row among them
MAX_WIDTH = 255  # the widest column Excel allows, in characters
FIRST_DATA_CELL = "A2"  # the panes freeze above it: the header row stays in view
LOSABLE_PARTS = ("xl/charts/", "xl/pivotTables/")
LOSS_WARNING = "the book has charts or pivot tables: they may be lost"


def _new_book() -> Workbook:
    book = Workbook()
    book.remove(book.active)
    return book


def _losable(path: Path) -> bool:
    with zipfile.ZipFile(path) as book:
        return any(member.startswith(LOSABLE_PARTS) for member in book.namelist())


def _replaced_sheet(book: Workbook, part: str) -> Worksheet:
    """An empty sheet `part` in the place of the old one, or the last one when the book has none."""
    index = book.sheetnames.index(part) if part in book.sheetnames else len(book.sheetnames)
    if part in book.sheetnames:
        book.remove(book[part])
    return book.create_sheet(part, index)


def _is_empty(sheet: Worksheet) -> bool:
    return (sheet.max_row, sheet.max_column) == (1, 1) and sheet["A1"].value is None


def _require_room(rows: int) -> None:
    if rows > MAX_ROWS:
        raise WriteRefused(
            f"the sheet would have {rows} rows, over the {MAX_ROWS} rows of an xlsx sheet.",
            action="Write csv or parquet: they have no row limit.",
        )


def _width(column: Iterable[Cell]) -> int:
    longest = max((len(str(cell.value)) for cell in column if cell.value is not None), default=0)
    return min(longest + settings().xlsx.column_padding, MAX_WIDTH)


def _lay_out(sheet: Worksheet, header: bool) -> None:
    for column in sheet.columns:
        sheet.column_dimensions[column[0].column_letter].width = _width(column)
    if header:
        sheet.freeze_panes = FIRST_DATA_CELL
        sheet.auto_filter.ref = sheet.dimensions


class XlsxAdapter(ExcelAdapter):
    name = "xlsx"
    extensions = (".xlsx",)
    appends = True

    def write_part(self, frame: pd.DataFrame, path: Path, part: str, options: WriteOptions) -> list[str]:
        existing = path.exists()
        with book_errors():
            warnings = [LOSS_WARNING] if existing and _losable(path) else []
            book = openpyxl.load_workbook(path) if existing else _new_book()
        sheet = self._sheet(book, part, frame, options)
        for row in plain(frame).itertuples(index=False, name=None):
            sheet.append(row)
        _lay_out(sheet, options.header)
        book.save(path)
        return warnings

    @staticmethod
    def _sheet(book: Workbook, part: str, frame: pd.DataFrame, options: WriteOptions) -> Worksheet:
        """The sheet the rows of `frame` go below: the old one for an append, else a new one with the header."""
        if options.mode is Mode.APPEND and part in book.sheetnames and not _is_empty(book[part]):
            sheet = book[part]
            if options.header:
                require_same_header([str(cell.value) for cell in sheet[1]], frame)
            _require_room(sheet.max_row + len(frame))
            return sheet
        _require_room(int(options.header) + len(frame))
        sheet = _replaced_sheet(book, part)
        if options.header:
            sheet.append(column_names(frame))
        return sheet


ADAPTER = XlsxAdapter()
