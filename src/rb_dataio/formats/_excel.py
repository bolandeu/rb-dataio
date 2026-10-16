"""The read of an Excel book (xlsx, xls, xlsb, ods) through python-calamine: a sheet is a part.

A cell keeps its type: text stays text, a number a number (a whole number is an int, as
xlsb and ods store every number as a float), a boolean a boolean, a date a date. An empty
cell is missing. Value normalisation then types the text columns with the leading-zero
and long-ID rules. `ExcelAdapter` is the base of the four book formats.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from python_calamine import CalamineWorkbook

from ..core.dataio.options import ReadOptions
from . import ContainerAdapter, Loaded

EMPTY_CELL = ""  # how calamine gives a cell with no value


def _value(cell: Any) -> Any:
    if isinstance(cell, str) and cell == EMPTY_CELL:
        return None
    if isinstance(cell, float) and cell.is_integer():
        return int(cell)
    return cell


class ExcelAdapter(ContainerAdapter):
    """A book of sheets: the parts are the sheet names in book order."""

    options = ()
    first_part = "Sheet1"

    def parts(self, path: Path) -> list[str]:
        with CalamineWorkbook.from_path(str(path)) as book:
            return list(book.sheet_names)

    def read_part(self, path: Path, part: str, options: ReadOptions) -> Loaded:
        with CalamineWorkbook.from_path(str(path)) as book:
            cells = book.get_sheet_by_name(part).to_python()
        rows = [[_value(cell) for cell in row] for row in cells]
        if options.header and rows:
            return Loaded(pd.DataFrame(rows[1:], columns=rows[0]))
        frame = pd.DataFrame(rows)
        frame.columns = pd.RangeIndex(frame.shape[1])  # no names: value normalisation calls them col1..colN
        return Loaded(frame)
