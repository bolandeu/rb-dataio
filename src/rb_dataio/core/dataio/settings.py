"""The settings of the table connector, read from the settings file the package ships (data/settings.toml).

`settings()` gives one section per concern: `BackupLimits` (the backup store), `WarningLimits`
(the loss warning, the repeated keys of a join), `XlsxLayout` (the layout of a written xlsx sheet), `GoogleEndpoints`
(where and for what a service-account key gets its tokens) and `SheetsCalls` (the batches,
the cell limit, the backoff and the timeout of the calls to Google Sheets).
"""

from __future__ import annotations

import functools
import tomllib
from importlib import resources

from pydantic import BaseModel, ConfigDict

_PACKAGE_NAME = __name__.split(".")[0]


class _Section(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)  # a missing or a misspelt key is an error


class BackupLimits(_Section):
    max_entries: int
    max_age_days: int
    max_total_mb: int
    max_object_mb: int


class WarningLimits(_Section):
    row_drop_share: float
    repeated_keys_named: int


class XlsxLayout(_Section):
    column_padding: int


class GoogleEndpoints(_Section):
    token_uri: str
    scopes: list[str]


class SheetsCalls(_Section):
    batch_rows: int
    max_cells: int
    retries: int
    backoff_seconds: float
    timeout_seconds: float


class Settings(_Section):
    backup: BackupLimits
    warnings: WarningLimits
    xlsx: XlsxLayout
    google: GoogleEndpoints
    gsheet: SheetsCalls


@functools.cache
def settings() -> Settings:
    text = resources.files(f"{_PACKAGE_NAME}.data").joinpath("settings.toml").read_text(encoding="utf-8")
    return Settings.model_validate(tomllib.loads(text))
