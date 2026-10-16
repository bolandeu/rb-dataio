"""The address: one string that names a source or a target, parsed into its parts.

`book.xlsx#Sheet1` is the path `book.xlsx` with the fragment `Sheet1` (a sheet or a
table, after the first `#`); `-` is stdin or stdout; `gsheet://<id>` and `https://…`
carry their scheme; `{column}`, `{n}` and `{stem}` in a path are placeholders. An
explicit `sheet=` or `table=` wins over the fragment, so a name with `#` still works.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePath

FILE = "file"
STDIO = "stdio"
STDIO_TEXT = "-"
_SCHEME = re.compile(r"^([A-Za-z][A-Za-z0-9+.-]*)://")
_PLACEHOLDER = re.compile(r"\{(\w+)\}")


@dataclass(frozen=True)
class Address:
    text: str  # as the caller wrote it: reports and errors name it
    scheme: str
    path: str  # a local path, an id or the rest of a URL after `<scheme>://`
    fragment: str | None  # the sheet or the table
    placeholders: tuple[str, ...]

    @property
    def suffix(self) -> str:
        return PurePath(self.path).suffix.lower()


def parse(text: str, *, sheet: str | None = None, table: str | None = None) -> Address:
    if text == STDIO_TEXT:
        scheme, rest = STDIO, text
    elif match := _SCHEME.match(text):
        scheme, rest = match[1].lower(), text[match.end() :]
    else:
        scheme, rest = FILE, text
    path, _, fragment = rest.partition("#")
    named = next((part for part in (sheet, table) if part is not None), fragment or None)
    return Address(text, scheme, path, named, tuple(_PLACEHOLDER.findall(path)))
