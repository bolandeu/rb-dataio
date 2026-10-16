"""CSV: encoding and delimiter are detected, the `excel` profile writes UTF-8-BOM with `;`.

Read: the encoding is the first of UTF-8 (with or without BOM) and cp1251 that decodes the
file, the delimiter is sniffed among `, ; tab |` on the first 64 KB. `encoding=` and `sep=`
replace the detection. Write: UTF-8 without BOM, `,` and `\\n`. `.tsv` (tsv.py) is the same
format with tab, never sniffed; the text decoder and the append helpers here also serve txt.py.
"""

from __future__ import annotations

import codecs
import csv
import io
import re
from pathlib import Path
from typing import ClassVar

import pandas as pd

from ..core.dataio.options import Mode, ReadOptions, SharedOptions, WriteOptions
from ..core.dataio.report import column_names
from ..core.errors import InvalidParameter
from . import FormatAdapter, Loaded

ENCODING = "utf-8"
BOM_ENCODING = "utf-8-sig"
FALLBACK_ENCODING = "cp1251"
EXCEL = "excel"
DELIMITERS = ",;\t|"
SNIFF_CHARACTERS = 64 * 1024
_BINARY = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f]")


def decode(data: bytes, encoding: str | None) -> tuple[str, str]:
    """The text of a file and the encoding it was read in: `encoding` if given, else detected."""
    if encoding:
        try:
            text = data.decode(encoding)
        except LookupError:
            raise InvalidParameter(f"Unknown encoding '{encoding}'.") from None
        return _text(text), encoding
    for candidate in (BOM_ENCODING if data.startswith(codecs.BOM_UTF8) else ENCODING, FALLBACK_ENCODING):
        try:
            return _text(data.decode(candidate)), candidate
        except UnicodeDecodeError:
            continue
    raise ValueError(f"binary or undecodable file: it is not text in {ENCODING} or {FALLBACK_ENCODING}.")


def _text(text: str) -> str:
    if _BINARY.search(text):
        raise ValueError("binary file: it has control characters that text does not.")
    return text


def sniff_delimiter(text: str) -> str:
    sample = text[:SNIFF_CHARACTERS]
    if len(text) > SNIFF_CHARACTERS:
        sample = sample[: sample.rfind("\n") + 1] or sample
    try:
        return csv.Sniffer().sniff(sample, delimiters=DELIMITERS).delimiter
    except csv.Error:
        return CsvAdapter.delimiter


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


class CsvAdapter(FormatAdapter):
    name = "csv"
    extensions = (".csv",)
    options = ("encoding", "sep")
    appends = True
    delimiter: ClassVar[str] = ","
    excel_delimiter: ClassVar[str] = ";"
    sniffs: ClassVar[bool] = True  # the delimiter is sniffed on read; False: `delimiter` is the default

    def read(self, path: Path, options: ReadOptions) -> Loaded:
        text, encoding = decode(path.read_bytes(), options.encoding)
        delimiter = options.sep or (sniff_delimiter(text) if self.sniffs else self.delimiter)
        frame = pd.read_csv(
            io.StringIO(text), sep=delimiter, header=None, dtype=str, keep_default_na=False, na_values=[""]
        )
        if options.header:
            frame = frame.iloc[1:].set_axis(frame.iloc[0].tolist(), axis="columns").reset_index(drop=True)
        else:
            frame.columns = pd.RangeIndex(frame.shape[1])  # no names: value normalisation calls them col1..colN
        return Loaded(frame, encoding, delimiter)

    def write(self, frame: pd.DataFrame, path: Path, options: WriteOptions) -> None:
        excel = self._is_excel(options)
        existing = existing_text(path, options) if options.mode is Mode.APPEND else None
        if existing is None:
            encoding = options.encoding or (BOM_ENCODING if excel else ENCODING)
            delimiter = options.sep or (self.excel_delimiter if excel else self.delimiter)
            path.write_bytes(self._render(frame, delimiter, options.header).encode(encoding))
            return
        text = existing[0]
        delimiter = options.sep or sniff_delimiter(text)
        if options.header:
            self._require_same_header(text, delimiter, frame)
        append_text(path, existing, self._render(frame, delimiter, header=False))

    @staticmethod
    def _is_excel(options: WriteOptions) -> bool:
        if options.profile not in (None, EXCEL):
            raise InvalidParameter(f"profile must be '{EXCEL}', not '{options.profile}'.")
        return options.profile == EXCEL

    @staticmethod
    def _render(frame: pd.DataFrame, delimiter: str, header: bool) -> str:
        return frame.to_csv(index=False, sep=delimiter, header=header, lineterminator="\n")

    @staticmethod
    def _require_same_header(text: str, delimiter: str, frame: pd.DataFrame) -> None:
        in_file = next(csv.reader(io.StringIO(text), delimiter=delimiter))
        in_data = column_names(frame)
        if in_file != in_data:
            raise ValueError(
                f"cannot append: the header of the file is {in_file}, the header of the data is {in_data}."
            )


ADAPTER = CsvAdapter()
