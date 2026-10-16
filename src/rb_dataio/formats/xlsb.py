"""xlsb: an Excel book that dataio reads (_excel.py) and never writes; xlsx is the one it writes."""

from __future__ import annotations

from ._excel import ExcelAdapter
from .xlsx import ADAPTER as XLSX


class XlsbAdapter(ExcelAdapter):
    name = "xlsb"
    extensions = (".xlsb",)
    written_as = XLSX.name


ADAPTER = XlsbAdapter()
