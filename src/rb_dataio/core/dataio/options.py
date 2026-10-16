"""The parameter vocabulary: the options of a read and of a write, the same words in every format and in the CLI.

`SharedOptions` are the options both sides have; in `convert` they take `in_` / `out_`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from enum import StrEnum
from typing import Any, Self

from ..errors import InvalidParameter


class Mode(StrEnum):
    """The write mode: what a write does with the data the target already has."""

    REPLACE = "replace"
    APPEND = "append"
    ERROR = "error"


@dataclass(frozen=True)
class SharedOptions:
    format: str | None
    sheet: str | None
    table: str | None
    encoding: str | None
    sep: str | None
    header: bool

    @classmethod
    def taken_from(cls, arguments: Mapping[str, Any], side: str | None = None) -> Self:
        """The options from a call's arguments; with `side`, a shared option is named `<side>_<option>`."""
        shared = {field.name for field in fields(SharedOptions)}

        def argument(name: str) -> Any:
            return arguments[f"{side}_{name}" if side and name in shared else name]

        return cls(**{field.name: argument(field.name) for field in fields(cls)})


@dataclass(frozen=True)
class ReadOptions(SharedOptions):
    as_text: bool
    dtypes: dict[str, str] | None
    limit: int | None

    @classmethod
    def reading_back(cls, written: SharedOptions) -> Self:
        """The options that read what a write with `written` options leaves: its shared options, every value as text."""
        shared = {field.name: getattr(written, field.name) for field in fields(SharedOptions)}
        return cls(**shared, as_text=True, dtypes=None, limit=None)

    def __post_init__(self) -> None:
        if self.limit is not None and self.limit < 0:
            raise InvalidParameter(f"limit must be 0 or more, not {self.limit}.")


@dataclass(frozen=True)
class WriteOptions(SharedOptions):
    mode: Mode
    profile: str | None
    overwrite: bool
    backup: bool
    dry_run: bool

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "mode", Mode(self.mode))  # frozen: the one place the value is set
        except ValueError:
            known = ", ".join(mode.value for mode in Mode)
            raise InvalidParameter(f"mode must be one of {known}, not '{self.mode}'.") from None
