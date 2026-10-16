"""xls: an Excel book that dataio reads (_excel.py) and never writes; xlsx is the one it writes."""

from __future__ import annotations

from ._excel import ExcelAdapter
from .xlsx import ADAPTER as XLSX


class XlsAdapter(ExcelAdapter):
    name = "xls"
    extensions = (".xls",)
    written_as = XLSX.name


ADAPTER = XlsAdapter()
