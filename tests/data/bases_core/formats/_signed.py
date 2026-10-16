"""A helper of the test formats alpha and beta: a CSV file after a signature line, with the extension `.db`.

Two formats share `.db` and claim a file by its signature, as SQLite and DuckDB do.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import ClassVar

import pandas as pd

from rb_dataio.core.dataio.options import ReadOptions
from rb_dataio.formats import FormatAdapter, Loaded


class SignedAdapter(FormatAdapter):
    extensions = (".db",)
    options = ()
    signature: ClassVar[bytes]

    def claims(self, path: Path) -> bool:
        with path.open("rb") as file:
            return file.read(len(self.signature)) == self.signature

    def read(self, path: Path, options: ReadOptions) -> Loaded:
        text = path.read_bytes().removeprefix(self.signature).decode("utf-8")
        return Loaded(pd.read_csv(io.StringIO(text), dtype=str))
