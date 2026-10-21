"""The parameter vocabulary: the options of a read and of a write, the same words in every format and in the CLI.

`SharedOptions` are the options both sides have; in `convert` they take `in_` / `out_`.
`query`, `source_column` and `strict` are of the read side only, so `convert` takes them without a prefix;
`start`, `value_input` (`ValueInput`), `split_by`, `chunk_rows`, `drop_split_column`, `keep_going`,
`columns` and `rename` (the target columns, columns.py)
are of the write side only. `JoinOptions` are the lookups, the keys (`on`, each a `Key`) and the kind (`How`) of a join (joins.py).
The batch parameters are read by the behaviour modules
(sources.py, targets.py, batch.py); the pipelines only pass them on.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from enum import StrEnum
from typing import Any, Self, TypeVar

from ..errors import InvalidParameter


class Mode(StrEnum):
    """The write mode: what a write does with the data the target already has."""

    REPLACE = "replace"
    APPEND = "append"
    ERROR = "error"


SOURCE_COLUMN = "_source"  # the column that names the source of each row of a merge

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
    source_column: str | None  # the column naming the source of each row of a merge; None leaves it out
    strict: bool  # a merge of sources with different columns is SCHEMA_MISMATCH, not a union

    @classmethod
    def reading_back(cls, written: SharedOptions) -> Self:
        """The options that read what a write with `written` options leaves: its shared options, every value as text."""
        shared = {field.name: getattr(written, field.name) for field in fields(SharedOptions)}
        return cls(**shared, as_text=True, dtypes=None, limit=None, query=None, source_column=None, strict=False)

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
    split_by: str | None  # a column: one target per value of it, in a target that is a template
    chunk_rows: int | None  # a number of rows: one numbered target per chunk, in a target that is a template
    drop_split_column: bool  # leave the `split_by` column out of the targets
    keep_going: bool  # a batch goes on after a failure and reports it in `errors`, else it stops at the first
    columns: list[str] | None  # the source columns the target keeps, in this order; None: all
    rename: dict[str, str] | None  # new names of the kept columns, old -> new; None: none

    def __post_init__(self) -> None:
        # frozen: the one place the values are set
        object.__setattr__(self, "mode", _member(Mode, "mode", self.mode))
        object.__setattr__(self, "value_input", _member(ValueInput, "value_input", self.value_input))
        if self.chunk_rows is not None and self.chunk_rows < 1:
            raise InvalidParameter(f"chunk_rows must be 1 or more, not {self.chunk_rows}.")


class How(StrEnum):
    """The kind of a join: which rows it keeps besides the main rows that found a match."""

    LEFT = "left"  # every main row
    RIGHT = "right"  # every lookup row
    INNER = "inner"  # matched rows only
    FULL = "full"  # every row of both sides


@dataclass(frozen=True)
class Key:
    """One key column of a join: its name in the main source and in the lookups."""

    main: str
    lookup: str

    @classmethod
    def named(cls, item: str) -> Self:
        """The key of one item of `on`: a name, or main_name=lookup_name."""
        main, equals, lookup = item.partition("=")
        if not main or (equals and not lookup):
            raise InvalidParameter(f"on has '{item}': give a column name, or main_name=lookup_name.")
        return cls(main, lookup or main)


@dataclass(frozen=True)
class JoinOptions:
    lookups: list[Any]  # the lookups, joined to the main source in this order
    on: list[str] | None  # the key columns: a name, or main_name=lookup_name
    how: How
    keys: list[Key] = field(init=False)  # `on` parsed

    @classmethod
    def taken_from(cls, arguments: Mapping[str, Any]) -> Self:
        """The options from a call's arguments; no `lookups` is none."""
        return cls(lookups=arguments["lookups"] or [], on=arguments["on"], how=arguments["how"])

    def __post_init__(self) -> None:
        object.__setattr__(self, "how", _member(How, "how", self.how))
        if not self.on:
            raise InvalidParameter("on must name the key columns: a name, or main_name=lookup_name.")
        object.__setattr__(self, "keys", [Key.named(item) for item in self.on])
        if not self.lookups:
            raise InvalidParameter("lookups must name at least one lookup.")
        if self.how is How.RIGHT and len(self.lookups) > 1:
            raise InvalidParameter(
                f"how 'right' joins one lookup, not {len(self.lookups)}: keep one, or use left, inner or full."
            )
