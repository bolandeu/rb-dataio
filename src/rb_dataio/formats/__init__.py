"""The formats: one module per format, each with an `ADAPTER` that reads and/or writes it.

A new format is one new module here and nothing else: `adapters()` finds every
module of this package, and `formats()` and the `FORMAT_UNKNOWN` list come from it.
An adapter has a read ability when it defines `read`, a write ability when it
defines `write`; `appends` and `options` it states itself, and a format that only reads
names in `written_as` the format that writes its kind of file. A write the format refuses
before it writes raises `WriteRefused`, with the action to take instead. A `TextAdapter` is a
format of plain text: it defines `parse` and `render`, and the same two serve its
files, stdin and stdout, and the in-memory text of `write()`. A `ContainerAdapter` is a
format of a file with named parts (sheets, tables): it lists the parts, reads one and
writes one, and the core gives every container the same choice of the part
(core/dataio/containers.py). A `BaseAdapter` is a container of tables (a base): it runs
SQL inside the base, counts the rows of its tables and writes a table in place, in one
transaction. Any adapter may run `query=` on its file itself (`query`) and may claim a file by its signature (`claims`),
so that formats that share an extension (`.db`) tell their files apart.
A module whose name starts with `_` is a helper, not a format.
"""

from __future__ import annotations

import codecs
import importlib
import pkgutil
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import ClassVar

import pandas as pd

from ..core.dataio.options import ReadOptions, WriteOptions
from ..core.errors import InvalidParameter

ENCODING = "utf-8"
BOM_ENCODING = "utf-8-sig"
FALLBACK_ENCODING = "cp1251"
_BINARY = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f]")


def decode(data: bytes, encoding: str | None) -> tuple[str, str]:
    """The text of `data` and its encoding: `encoding` if given, else UTF-8 (with or without BOM) or cp1251."""
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


@dataclass(frozen=True)
class Loaded:
    """A table an adapter read, with the encoding and the delimiter it used (None where the format has none).

    `infers_types` False: value normalisation keeps the text columns as they are (a phrase list stays text).
    `warnings` are what the read tells the report about.
    """

    frame: pd.DataFrame
    encoding: str | None = None
    delimiter: str | None = None
    infers_types: bool = True
    warnings: tuple[str, ...] = ()


class WriteRefused(ValueError):
    """A write the format refuses before it writes anything; `action` is what to do instead."""

    def __init__(self, message: str, *, action: str) -> None:
        super().__init__(message)
        self.action = action


class FormatAdapter:
    name: ClassVar[str]
    extensions: ClassVar[tuple[str, ...]]  # lower case, with the dot
    options: ClassVar[tuple[str, ...]]  # the parameters this format honours
    appends: ClassVar[bool] = False
    written_as: ClassVar[str | None] = None  # a format that cannot write: the one that writes its kind of file

    def read(self, path: Path, options: ReadOptions) -> Loaded:
        raise NotImplementedError

    def write(self, frame: pd.DataFrame, path: Path, options: WriteOptions) -> None:
        raise NotImplementedError

    def claims(self, path: Path) -> bool:
        """True when `path` has this format's signature; asked only of the formats that share its extension."""
        return False

    def query(self, path: Path, sql: str, options: ReadOptions) -> Loaded | None:
        """The result of `sql` run on the file itself, the file being the table `data` of `query=`.

        None: the format cannot, and the core runs the SQL over the table it reads (core/dataio/query.py).
        """
        return None

    @property
    def reads(self) -> bool:
        return type(self).read is not FormatAdapter.read

    @property
    def writes(self) -> bool:
        return type(self).write is not FormatAdapter.write


class TextAdapter(FormatAdapter):
    """A format of plain text: a read decodes the file and parses the text, a write renders the text and encodes it."""

    def parse(self, text: str, options: ReadOptions) -> Loaded:
        raise NotImplementedError

    def render(self, frame: pd.DataFrame, options: WriteOptions) -> str:
        raise NotImplementedError

    def load(self, data: bytes, options: ReadOptions) -> Loaded:
        """The table of the bytes of a file or of stdin, with the encoding they were read in."""
        text, encoding = decode(data, options.encoding)
        return replace(self.parse(text, options), encoding=encoding)

    def read(self, path: Path, options: ReadOptions) -> Loaded:
        return self.load(path.read_bytes(), options)

    def write(self, frame: pd.DataFrame, path: Path, options: WriteOptions) -> None:
        path.write_bytes(self.render(frame, options).encode(options.encoding or ENCODING))


class ContainerAdapter(FormatAdapter):
    """A format of a file with named parts (sheets, tables): the core picks the part, the adapter reads or writes it.

    `write_part` gets a copy of the current file (no file for a new one) and changes only `part`;
    it returns the warnings of the write, for example what the format may lose.
    """

    first_part: ClassVar[str]  # the name of the part a new file gets when the address names none

    def parts(self, path: Path) -> list[str]:
        raise NotImplementedError

    def read_part(self, path: Path, part: str, options: ReadOptions) -> Loaded:
        raise NotImplementedError

    def write_part(self, frame: pd.DataFrame, path: Path, part: str, options: WriteOptions) -> list[str]:
        raise NotImplementedError

    @property
    def reads(self) -> bool:
        return type(self).read_part is not ContainerAdapter.read_part

    @property
    def writes(self) -> bool:
        return type(self).write_part is not ContainerAdapter.write_part


class BaseAdapter(ContainerAdapter):
    """A format of a base: a database file whose parts are tables.

    `query` runs the SQL inside the base, where the tables have their own names. `write_part`
    gets the base itself, not a copy, and writes the table in one transaction: the core
    neither copies nor replaces the file, and its backup holds the old rows of that table
    only. An error of the database is raised as a ValueError with the database's message.
    """

    def query(self, path: Path, sql: str, options: ReadOptions) -> Loaded:
        raise NotImplementedError

    def row_counts(self, path: Path) -> dict[str, int]:
        """The number of rows of every table, by name: `info` lists them."""
        raise NotImplementedError


def adapters() -> list[FormatAdapter]:
    """The adapter of every module of this package but the helpers (`_` first), by format name."""
    modules = (
        importlib.import_module(f"{__name__}.{info.name}")
        for info in pkgutil.iter_modules(__path__)
        if not info.name.startswith("_")
    )
    return sorted((module.ADAPTER for module in modules), key=lambda adapter: adapter.name)
