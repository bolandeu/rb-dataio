"""The report: what dataio read and wrote. The library returns it, the CLI puts it in its success envelope.

A dry run reports the target as a `PlannedTarget` (whether it exists, its rows before and after);
a `Backup` is one entry of the backup store, listed by `backups()` and named in a restore report.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from pydantic import BaseModel, Field, SerializeAsAny

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
    rows: int | None  # None only in a restore of a backup whose content dataio could not read
    columns: list[str] | None


class PlannedTarget(TargetPart):
    """The target part of a dry run: whether the target exists and its rows before and after the write."""

    exists: bool
    rows_before: int | None  # None when the target exists but dataio cannot read it
    rows_after: int | None


class Backup(_Part):
    """One kept backup: what `backups()` lists and `restore(id)` brings back."""

    id: str
    time: str  # ISO 8601, UTC
    target: str  # the absolute path of the replaced target
    format: str
    rows: int | None  # None when dataio could not read the old content
    columns: list[str] | None
    table: str | None = None  # a table of a base: the content is its old rows only, as parquet


class Report(_Part):
    source: SourcePart | None = None
    target: SerializeAsAny[TargetPart] | None = None  # a PlannedTarget in a dry run
    backup: Backup | None = None  # the backup a restore brings back
    warnings: list[str] = Field(default_factory=list)
    data: Any = None  # the data of an object format written to `-` (records under the CLI's --json)

    def to_dict(self) -> dict[str, Any]:
        """A side that took no part (no source in `write()`) is left out."""
        return {key: value for key, value in super().to_dict().items() if value is not None}


class Info(_Part):
    """What `info()` tells about a source: the source part of a report, the column types and the first rows.

    `parts` are the sheets or tables of a container file; empty for any other source.
    """

    source: SourcePart
    types: dict[str, str]
    preview: list[dict[str, Any]]
    parts: list[str] = Field(default_factory=list)


class FormatInfo(_Part):
    """One format of the registry as `formats()` lists it."""

    name: str
    extensions: list[str]
    read: bool
    write: bool
    append: bool
    options: list[str]
