"""A container format that tests/test_containers.py adds to the formats package: a zip with one CSV per part.

The parts are the CSV members in zip order, named without `.csv`. Any other member stands for
what a real format may lose on a write (a chart): the write keeps it and warns about it.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd

from rb_dataio.core.dataio.options import ReadOptions, WriteOptions
from rb_dataio.formats import ContainerAdapter, Loaded

CSV = ".csv"


class ZipCsvAdapter(ContainerAdapter):
    name = "zipcsv"
    extensions = (".zcsv",)
    options = ()
    first_part = "Sheet1"

    def parts(self, path: Path) -> list[str]:
        with zipfile.ZipFile(path) as book:
            return [member.removesuffix(CSV) for member in book.namelist() if member.endswith(CSV)]

    def read_part(self, path: Path, part: str, options: ReadOptions) -> Loaded:
        with zipfile.ZipFile(path) as book:
            text = book.read(part + CSV).decode("utf-8")
        return Loaded(pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False, na_values=[""]))

    def write_part(self, frame: pd.DataFrame, path: Path, part: str, options: WriteOptions) -> list[str]:
        members: dict[str, bytes] = {}
        if path.exists():
            with zipfile.ZipFile(path) as book:
                members = {member: book.read(member) for member in book.namelist()}
        members[part + CSV] = frame.to_csv(index=False, lineterminator="\n").encode("utf-8")
        with zipfile.ZipFile(path, "w") as book:
            for member, data in members.items():
                book.writestr(member, data)
        return ["charts may be lost"] if any(not member.endswith(CSV) for member in members) else []


ADAPTER = ZipCsvAdapter()
