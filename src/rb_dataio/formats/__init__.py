"""The formats: one module per format, each with an `ADAPTER` that reads and/or writes it.

A new format is one new module here and nothing else: `adapters()` finds every
module of this package, and `formats()` and the `FORMAT_UNKNOWN` list come from it.
An adapter has a read ability when it defines `read`, a write ability when it
defines `write`; `appends`, `infers_types` and `options` it states itself.
"""

from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import pandas as pd

from ..core.dataio.options import ReadOptions, WriteOptions


@dataclass(frozen=True)
class Loaded:
    """A table an adapter read, with the encoding and the delimiter it used (None where the format has none)."""

    frame: pd.DataFrame
    encoding: str | None = None
    delimiter: str | None = None


class FormatAdapter:
    name: ClassVar[str]
    extensions: ClassVar[tuple[str, ...]]  # lower case, with the dot
    options: ClassVar[tuple[str, ...]]  # the parameters this format honours
    appends: ClassVar[bool] = False
    infers_types: ClassVar[bool] = True  # False: value normalisation keeps the text columns as they are

    def read(self, path: Path, options: ReadOptions) -> Loaded:
        raise NotImplementedError

    def write(self, frame: pd.DataFrame, path: Path, options: WriteOptions) -> None:
        raise NotImplementedError

    @property
    def reads(self) -> bool:
        return type(self).read is not FormatAdapter.read

    @property
    def writes(self) -> bool:
        return type(self).write is not FormatAdapter.write


def adapters() -> list[FormatAdapter]:
    """The adapter of every module of this package, by format name."""
    modules = (importlib.import_module(f"{__name__}.{info.name}") for info in pkgutil.iter_modules(__path__))
    return sorted((module.ADAPTER for module in modules), key=lambda adapter: adapter.name)
