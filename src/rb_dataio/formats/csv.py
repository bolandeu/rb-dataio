"""CSV: encoding and delimiter are detected, the `excel` profile writes UTF-8-BOM with `;`.

Read: the encoding is the first of UTF-8 (with or without BOM) and cp1251 that decodes the
file, the delimiter is sniffed among `, ; tab |` on the first 64 KB. `encoding=` and `sep=`
replace the detection. `query=` over a UTF-8 file with a header is run by DuckDB on the
file itself, with the delimiter detected the same way; any other file is read first
(core/dataio/query.py). Write: UTF-8 without BOM, `,` and `\\n`. `.tsv` (tsv.py) is the same
format with tab, never sniffed; the append helpers here also serve txt.py, and the header
check of an append serves xlsx.py.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import ClassVar

import pandas as pd

from ..core.dataio import query
from ..core.dataio.options import Mode, ReadOptions, SharedOptions, WriteOptions
from ..core.dataio.report import column_names
from ..core.errors import InvalidParameter
from . import BOM_ENCODING, ENCODING, Loaded, TextAdapter, decode

EXCEL = "excel"
DELIMITERS = ",;\t|"
SNIFF_CHARACTERS = 64 * 1024


def sniff_delimiter(text: str) -> str | None:
    """The delimiter every line of the first 64 KB agrees on; None when there is none."""
    sample = text[:SNIFF_CHARACTERS]
    if len(text) > SNIFF_CHARACTERS:
        sample = sample[: sample.rfind("\n") + 1] or sample
    try:
        return csv.Sniffer().sniff(sample, delimiters=DELIMITERS).delimiter
    except csv.Error:
        return None


def existing_text(path: Path, options: SharedOptions) -> tuple[str, str] | None:
    """The text and the encoding of the file an append goes to; None when there is nothing to add to."""
    if not path.exists() or path.stat().st_size == 0:
        return None
    return decode(path.read_bytes(), options.encoding)


def append_text(path: Path, existing: tuple[str, str], text: str) -> None:
    """Add `text` below the existing content, in the encoding of the file."""
    content, encoding = existing
    separator = "" if content.endswith("\n") else "\n"
    with path.open("ab") as handle:
        handle.write((separator + text).encode(ENCODING if encoding == BOM_ENCODING else encoding))


def require_same_header(in_file: list[str], frame: pd.DataFrame) -> None:
    """Refuse an append whose data has another header than the file it goes to."""
    in_data = column_names(frame)
    if in_file != in_data:
        raise ValueError(f"cannot append: the header of the file is {in_file}, the header of the data is {in_data}.")


class CsvAdapter(TextAdapter):
    name = "csv"
    extensions = (".csv",)
    options = ("encoding", "sep")
    appends = True
    delimiter: ClassVar[str] = ","
    excel_delimiter: ClassVar[str] = ";"
    sniffs: ClassVar[bool] = True  # the delimiter is sniffed on read; False: `delimiter` is the default

    def parse(self, text: str, options: ReadOptions) -> Loaded:
        delimiter = self._read_delimiter(text, options)
        frame = pd.read_csv(
            io.StringIO(text), sep=delimiter, header=None, dtype=str, keep_default_na=False, na_values=[""]
        )
        if options.header:
            frame = frame.iloc[1:].set_axis(frame.iloc[0].tolist(), axis="columns").reset_index(drop=True)
        else:
            frame.columns = pd.RangeIndex(frame.shape[1])  # no names: value normalisation calls them col1..colN
        return Loaded(frame, delimiter=delimiter)

    def query(self, path: Path, sql: str, options: ReadOptions) -> Loaded | None:
        with path.open("rb") as file:
            head = file.read(SNIFF_CHARACTERS)
            if file.read(1):  # a cut inside a character would not decode: whole lines only
                head = head[: head.rfind(b"\n") + 1] or head
        try:
            text, encoding = decode(head, options.encoding)
        except ValueError:
            return None
        if encoding not in (ENCODING, BOM_ENCODING) or not options.header:
            return None
        delimiter = self._read_delimiter(text, options)
        function = f"read_csv({query.literal(str(path))}, delim={query.literal(delimiter)}, header=true)"
        return Loaded(query.over_file(function, sql), encoding=encoding, delimiter=delimiter, infers_types=False)

    def render(self, frame: pd.DataFrame, options: WriteOptions) -> str:
        delimiter = options.sep or (self.excel_delimiter if self._is_excel(options) else self.delimiter)
        return self._render(frame, delimiter, options.header)

    def write(self, frame: pd.DataFrame, path: Path, options: WriteOptions) -> None:
        existing = existing_text(path, options) if options.mode is Mode.APPEND else None
        if existing is None:
            encoding = options.encoding or (BOM_ENCODING if self._is_excel(options) else ENCODING)
            path.write_bytes(self.render(frame, options).encode(encoding))
            return
        text = existing[0]
        delimiter = options.sep or sniff_delimiter(text) or self.delimiter
        if options.header:
            require_same_header(next(csv.reader(io.StringIO(text), delimiter=delimiter)), frame)
        append_text(path, existing, self._render(frame, delimiter, header=False))

    def _read_delimiter(self, text: str, options: ReadOptions) -> str:
        sniffed = sniff_delimiter(text) if self.sniffs else None
        return options.sep or sniffed or self.delimiter

    @staticmethod
    def _is_excel(options: WriteOptions) -> bool:
        if options.profile not in (None, EXCEL):
            raise InvalidParameter(f"profile must be '{EXCEL}', not '{options.profile}'.")
        return options.profile == EXCEL

    @staticmethod
    def _render(frame: pd.DataFrame, delimiter: str, header: bool) -> str:
        return frame.to_csv(index=False, sep=delimiter, header=header, lineterminator="\n")


ADAPTER = CsvAdapter()
