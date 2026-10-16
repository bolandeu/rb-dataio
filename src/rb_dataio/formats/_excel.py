"""The read of an Excel book (xlsx, xls, xlsb, ods) through python-calamine: a sheet is a part.

A cell keeps its type: text stays text, a number a number (a whole number is an int, as
xlsb and ods store every number as a float), a boolean a boolean, a date a date. An empty
cell is missing. Value normalisation then types the text columns with the leading-zero
and long-ID rules. `ExcelAdapter` is the base of the four book formats; inside
`book_errors()` a file that is no valid book raises a ValueError, which the core reports.
"""

from __future__ import annotations

import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl.utils.exceptions import InvalidFileException
from python_calamine import CalamineError, CalamineWorkbook

from ..core.dataio.options import ReadOptions
from . import ContainerAdapter, Loaded

EMPTY_CELL = ""  # how calamine gives a cell with no value
EXACT_WHOLE_NUMBERS = 2**53  # a float holds every whole number below this exactly
_BOOK_ERRORS = (CalamineError, zipfile.BadZipFile, InvalidFileException)  # the engines' "this is no book"


@contextmanager
def book_errors() -> Iterator[None]:
    """Turn an engine's error about a file that is no valid book into a ValueError."""
    try:
        yield
    except _BOOK_ERRORS as exc:
        raise ValueError(f"not a valid book of its format: {exc}") from exc


def _value(cell: Any) -> Any:
    if isinstance(cell, str) and cell == EMPTY_CELL:
        return None
    if isinstance(cell, float) and cell.is_integer() and abs(cell) < EXACT_WHOLE_NUMBERS:
        return int(cell)
    return cell


class ExcelAdapter(ContainerAdapter):
    """A book of sheets: the parts are the sheet names in book order."""

    options = ()
    first_part = "Sheet1"

    def parts(self, path: Path) -> list[str]:
        with book_errors(), CalamineWorkbook.from_path(str(path)) as book:
            return list(book.sheet_names)

    def read_part(self, path: Path, part: str, options: ReadOptions) -> Loaded:
        with book_errors(), CalamineWorkbook.from_path(str(path)) as book:
            cells = book.get_sheet_by_name(part).to_python()
        rows = [[_value(cell) for cell in row] for row in cells]
        if options.header and rows:
            return Loaded(pd.DataFrame(rows[1:], columns=rows[0]))
        frame = pd.DataFrame(rows)
        frame.columns = pd.RangeIndex(frame.shape[1])  # no names: value normalisation calls them col1..colN
        return Loaded(frame)
