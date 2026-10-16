"""TSV: the CSV format with tab, never sniffed. `sep=` still wins; the `excel` profile keeps the tab."""

from __future__ import annotations

from typing import ClassVar

from .csv import CsvAdapter


class TsvAdapter(CsvAdapter):
    name = "tsv"
    extensions = (".tsv",)
    delimiter: ClassVar[str] = "\t"
    excel_delimiter: ClassVar[str] = "\t"
    sniffs: ClassVar[bool] = False


ADAPTER = TsvAdapter()
