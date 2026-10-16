"""The parameter vocabulary: the options of a read and of a write, the same words in every format and in the CLI.

`SharedOptions` are the options both sides have; in `convert` they take `in_` / `out_`.
`query` is of the read side only, so `convert` takes it without a prefix; `start` and
`value_input` (`ValueInput`) are of the write side only.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from enum import StrEnum
from typing import Any, Self, TypeVar

from ..errors import InvalidParameter


class Mode(StrEnum):
    """The write mode: what a write does with the data the target already has."""

    REPLACE = "replace"
    APPEND = "append"
    ERROR = "error"


_Member = TypeVar("_Member", bound=StrEnum)


class ValueInput(StrEnum):
    """How a service takes the written values: `raw` as they are (`007` and `=1+1` stay text), `user` as typed."""

    RAW = "raw"
    USER = "user"


def _member(enum: type[_Member], name: str, value: object) -> _Member:
    """`value` as a member of `enum`; INVALID_ARGUMENTS naming the parameter `name` and the known values."""
    try:
        return enum(value)
    except ValueError:
        known = ", ".join(member.value for member in enum)
        raise InvalidParameter(f"{name} must be one of {known}, not '{value}'.") from None


@dataclass(frozen=True)
class SharedOptions:
    format: str | None
    sheet: str | None
    table: str | None
    encoding: str | None
    sep: str | None
    header: bool
    credentials: str | None  # a key file for a remote source or target; None: the standard order

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
    query: str | None  # SQL whose result is the table read (core/dataio/query.py)

    @classmethod
    def reading_back(cls, written: SharedOptions) -> Self:
        """The options that read what a write with `written` options leaves: its shared options, every value as text."""
        shared = {field.name: getattr(written, field.name) for field in fields(SharedOptions)}
        return cls(**shared, as_text=True, dtypes=None, limit=None, query=None)

    def __post_init__(self) -> None:
        if self.limit is not None and self.limit < 0:
            raise InvalidParameter(f"limit must be 0 or more, not {self.limit}.")


@dataclass(frozen=True)
class WriteOptions(SharedOptions):
    mode: Mode
    start: str | None  # the top-left cell of the written table in a sheet of a service; None: A1
    value_input: ValueInput
    profile: str | None
    overwrite: bool
    backup: bool
    dry_run: bool

    def __post_init__(self) -> None:
        # frozen: the one place the values are set
        object.__setattr__(self, "mode", _member(Mode, "mode", self.mode))
        object.__setattr__(self, "value_input", _member(ValueInput, "value_input", self.value_input))
