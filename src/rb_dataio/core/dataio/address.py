"""The address: one string that names a source or a target, parsed into its parts.

`book.xlsx#Sheet1` is the path `book.xlsx` with the fragment `Sheet1` (a sheet or a
table, after the first `#`); `-` is stdin or stdout; `gsheet://<id>` and `https://…`
carry their scheme; `{column}`, `{n}` and `{stem}` in a path are placeholders. An
explicit `sheet=` or `table=` wins over the fragment, so a name with `#` still works.
A Google Sheets browser URL is the address `gsheet://<id>` of its spreadsheet, with the
sheet by its `gid` when the URL has one (a 'Publish to web' link stays an https URL).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePath

FILE = "file"
STDIO = "stdio"
STDIO_TEXT = "-"
GOOGLE_SHEETS = "gsheet"
_SCHEME = re.compile(r"^([A-Za-z][A-Za-z0-9+.-]*)://")
_PLACEHOLDER = re.compile(r"\{(\w+)\}")
# /d/<id>, then /edit or /view (or nothing) and the query; never /d/e/<id>/pub, the 'Publish to web' link
_GOOGLE_SHEETS_URL = re.compile(
    r"https?://docs\.google\.com/spreadsheets/d/(?P<id>[\w-]+)(?:/(?:edit|view)?)?(?P<rest>[?#].*)?", re.IGNORECASE
)
_GID = re.compile(r"[?#&]gid=(\d+)")


@dataclass(frozen=True)
class Address:
    text: str  # as the caller wrote it: reports and errors name it
    scheme: str
    path: str  # a local path, an id or the rest of a URL after `<scheme>://`
    fragment: str | None  # the sheet or the table
    placeholders: tuple[str, ...]
    gid: int | None = None  # the sheet of a Google Sheets URL by its id, when no name is given

    @property
    def suffix(self) -> str:
        return PurePath(self.path).suffix.lower()

    @property
    def place(self) -> str:
        """The address without its fragment: what a backup of a part of a remote container names."""
        return f"{self.scheme}://{self.path}"


def parse(text: str, *, sheet: str | None = None, table: str | None = None) -> Address:
    if google := _GOOGLE_SHEETS_URL.fullmatch(text):
        return _google_sheets(text, google, sheet, table)
    if text == STDIO_TEXT:
        scheme, rest = STDIO, text
    elif match := _SCHEME.match(text):
        scheme, rest = match[1].lower(), text[match.end() :]
    else:
        scheme, rest = FILE, text
    path, _, fragment = rest.partition("#")
    named = _named(sheet, table, fragment or None)
    return Address(text, scheme, path, named, tuple(_PLACEHOLDER.findall(path)))


def _google_sheets(text: str, url: re.Match[str], sheet: str | None, table: str | None) -> Address:
    named = _named(sheet, table, None)
    gid = _GID.search(url["rest"] or "") if named is None else None
    return Address(text, GOOGLE_SHEETS, url["id"], named, (), gid=int(gid[1]) if gid else None)


def _named(sheet: str | None, table: str | None, fragment: str | None) -> str | None:
    """The part an explicit `sheet=` or `table=` names, else the fragment."""
    return next((part for part in (sheet, table) if part is not None), fragment)
