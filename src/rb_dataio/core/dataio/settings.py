"""The settings of the table connector, read from the settings file the package ships (data/settings.toml).

`settings()` gives one section per concern: `BackupLimits` (the backup store), `WarningLimits`
(the loss warning), `XlsxLayout` (the layout of a written xlsx sheet) and `GoogleEndpoints`
(where and for what a service-account key gets its tokens).
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


class XlsxLayout(_Section):
    column_padding: int


class GoogleEndpoints(_Section):
    token_uri: str
    scopes: list[str]


class Settings(_Section):
    backup: BackupLimits
    warnings: WarningLimits
    xlsx: XlsxLayout
    google: GoogleEndpoints


@functools.cache
def settings() -> Settings:
    text = resources.files(f"{_PACKAGE_NAME}.data").joinpath("settings.toml").read_text(encoding="utf-8")
    return Settings.model_validate(tomllib.loads(text))
