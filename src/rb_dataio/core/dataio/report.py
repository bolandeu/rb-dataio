"""The report: what dataio read and wrote. The library returns it, the CLI puts it in its success envelope."""

from __future__ import annotations

from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

from .options import Mode


def column_names(frame: pd.DataFrame) -> list[str]:
    return [str(column) for column in frame.columns]


class _Part(BaseModel):
    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class SourcePart(_Part):
    uri: str
    format: str
    encoding: str | None
    delimiter: str | None
    rows: int
    columns: list[str]


class TargetPart(_Part):
    uri: str
    format: str
    mode: Mode
    rows: int
    columns: list[str]


class Report(_Part):
    source: SourcePart | None = None
    target: TargetPart | None = None
    warnings: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """A side that took no part (no source in `write()`) is left out."""
        return {key: value for key, value in super().to_dict().items() if value is not None}


class Info(_Part):
    """What `info()` tells about a source: the source part of a report, the column types and the first rows."""

    source: SourcePart
    types: dict[str, str]
    preview: list[dict[str, Any]]


class FormatInfo(_Part):
    """One format of the registry as `formats()` lists it."""

    name: str
    extensions: list[str]
    read: bool
    write: bool
    append: bool
    options: list[str]


class Backup(_Part):
    """One kept backup: what `backups()` lists and `restore(id)` brings back."""

    id: str
    time: str
    target: str
    rows: int
