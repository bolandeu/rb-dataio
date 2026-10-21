"""The report: what dataio read and wrote. The library returns it, the CLI puts it in its success envelope.

A dry run reports the target as a `PlannedTarget` (whether it exists, its rows before and after);
a batch reports `targets` (`BatchTarget`, `PlannedBatchTarget` in a dry run) and, when some failed, `errors` (`BatchError`);
a join reports `lookups` (`LookupPart`: how many main rows found a match in each lookup);
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


class LookupPart(_Part):
    """One lookup of a join: its address, its rows and how many main rows found a match in it.

    `matched` and `unmatched` add up to the rows the lookup was joined to; `empty_keys` are the unmatched
    ones with an empty key cell.
    """

    uri: str
    rows: int
    matched: int
    unmatched: int
    empty_keys: int


class PlannedTarget(TargetPart):
    """The target part of a dry run: whether the target exists and its rows before and after the write."""

    exists: bool
    rows_before: int | None  # None when the target exists but dataio cannot read it
    rows_after: int | None


class BatchTarget(_Part):
    """One target of a batch: where it was written and its rows."""

    uri: str
    rows: int


class PlannedBatchTarget(BatchTarget):
    """One target of a batch in a dry run: whether it exists and its rows before and after the write."""

    exists: bool
    rows_before: int | None
    rows_after: int | None


class BatchError(_Part):
    """One failure of a batch run with `keep_going`: the address that failed and the error code and message."""

    uri: str
    code: str
    message: str


class Backup(_Part):
    """One kept backup: what `backups()` lists and `restore(id)` brings back."""

    id: str
    time: str  # ISO 8601, UTC
    target: str  # the absolute path of the replaced target, or the place of a remote container (gsheet://<id>)
    format: str
    rows: int | None  # None when dataio could not read the old content
    columns: list[str] | None
    table: str | None = None  # a table of a base or a part of a remote container: its old rows only, as parquet


class Report(_Part):
    source: SourcePart | None = None
    target: SerializeAsAny[TargetPart] | None = None  # a PlannedTarget in a dry run
    targets: list[SerializeAsAny[BatchTarget]] | None = None  # a batch: every target written (or planned)
    errors: list[BatchError] | None = None  # a batch that failed in part: the failures, so the run is not ok
    backup: Backup | None = None  # the backup a restore brings back
    lookups: list[LookupPart] | None = None  # a join: one entry per lookup, in order
    warnings: list[str] = Field(default_factory=list)
    data: Any = None  # the data of an object format written to `-` (records under the CLI's --json)

    def to_dict(self) -> dict[str, Any]:
        """A side that took no part (no source in `write()`) is left out."""
        return {key: value for key, value in super().to_dict().items() if value is not None}


class Info(_Part):
    """What `info()` tells about a source: the source part of a report, the column types and the first rows.

    `parts` are the sheets or tables of a container file; empty for any other source.
    `part_rows` are the rows of each table of a base; empty for any other source.
    """

    source: SourcePart
    types: dict[str, str]
    preview: list[dict[str, Any]]
    parts: list[str] = Field(default_factory=list)
    part_rows: dict[str, int] = Field(default_factory=dict)


class FormatInfo(_Part):
    """One format of the registry as `formats()` lists it."""

    name: str
    extensions: list[str]
    read: bool
    write: bool
    append: bool
    options: list[str]
