"""The join (Соединение): the main source with the columns of its lookups, matched by the named key columns.

    refuse a target that is a source -> read the main source and every lookup -> check their key columns
    -> each lookup in order: key text -> DuckDB pairs the rows -> the table of the pairs -> its `LookupPart`
    -> the write path of convert (pipeline.write_frame)

A key cell compares as text with outer spaces trimmed, case and ё kept; an empty one matches nothing. The rows
keep the order of the main source; a lookup row that matched no main row (right, full) comes after them, with
its key in the main key column. A repeated lookup key repeats the main rows it matches, and a warning names it.
A lookup column whose name the table already has gets the suffix of its lookup: the part of the address, else
the file stem, else `lookup<N>` for a Python object; a suffix taken twice gets `_2` (values.unique).
`join` is the library's join() once its options are taken (api.py).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import PurePath

import duckdb
import pandas as pd

from ..errors import InvalidParameter
from . import objects, pipeline, values
from .address import parse
from .options import How, JoinOptions, Key, ReadOptions, WriteOptions
from .report import LookupPart, Report, SourcePart, column_names
from .settings import settings

_POSITION = "position"  # the row number of a side, in the tables DuckDB pairs
_MAIN, _LOOKUP = "main_row", "lookup_row"  # the paired row numbers; -1 where a side has none
_NONE = -1


@dataclass(frozen=True)
class _Lookup:
    """A lookup as read: its table, its source part, the warnings of the read and the suffix of its columns."""

    frame: pd.DataFrame
    part: SourcePart
    warnings: list[str]
    suffix: str


def join(source: object, target: str, options: JoinOptions, reading: ReadOptions, writing: WriteOptions) -> Report:
    """Join the lookups to `source` and write the table to `target`; the report has the lookups' counts."""
    for named in (source, *options.lookups):
        if isinstance(named, str | os.PathLike):
            pipeline.refuse_over_source(os.fspath(named), target, writing)
    table, source_part, warnings = pipeline.read_frame(source, reading)
    _require_keys(table, [key.main for key in options.keys], f"the main source '{source_part.uri}'")
    lookups = _read_lookups(options, reading)
    parts: list[LookupPart] = []
    for lookup in lookups:
        table, part, joined = _joined(table, lookup, options)
        parts.append(part)
        warnings += [*lookup.warnings, *joined]
    report = pipeline.write_frame(table, target, writing)
    return report.model_copy(
        update={"source": source_part, "lookups": parts, "warnings": [*warnings, *report.warnings]}
    )


def _read_lookups(options: JoinOptions, reading: ReadOptions) -> list[_Lookup]:
    """Every lookup read, its key columns checked, with a suffix no other lookup has."""
    lookups: list[_Lookup] = []
    for position, source in enumerate(options.lookups, start=1):
        frame, part, warnings = pipeline.read_frame(source, reading)
        _require_keys(frame, [key.lookup for key in options.keys], f"the lookup '{part.uri}'")
        suffix = values.unique(_suffix(source, position, reading), [lookup.suffix for lookup in lookups])
        lookups.append(_Lookup(frame, part, warnings, suffix))
    return lookups


def _suffix(source: object, position: int, reading: ReadOptions) -> str:
    """The part of the address, else its file stem; `lookup<position>` for a Python object or a text."""
    if isinstance(source, str | os.PathLike) and not objects.is_text(os.fspath(source), reading):
        address = parse(os.fspath(source), sheet=reading.sheet, table=reading.table)
        return address.fragment or PurePath(address.path).stem
    return f"lookup{position}"


def _require_keys(frame: pd.DataFrame, names: list[str], side: str) -> None:
    have = column_names(frame)
    for name in names:
        if name not in have:
            raise InvalidParameter(
                f"on names the column '{name}', which {side} does not have. Columns there are: {', '.join(have)}."
            )


def _joined(table: pd.DataFrame, lookup: _Lookup, options: JoinOptions) -> tuple[pd.DataFrame, LookupPart, list[str]]:
    """`table` with the columns of `lookup`, its part of the report and the warning about repeated keys."""
    main_keys = _key_text(table, [key.main for key in options.keys])
    lookup_keys = _key_text(lookup.frame, [key.lookup for key in options.keys])
    pairs = _pairs(main_keys, lookup_keys, options.how)
    joined = pd.concat(
        [_main_side(table, lookup.frame, pairs, options.keys), _lookup_side(table, lookup, pairs, options.keys)],
        axis="columns",
    )
    matched = pairs[_MAIN][(pairs[_MAIN] != _NONE) & (pairs[_LOOKUP] != _NONE)]
    part = LookupPart(
        uri=lookup.part.uri,
        rows=len(lookup.frame),
        matched=matched.nunique(),
        unmatched=len(table) - matched.nunique(),
        empty_keys=int(main_keys.isna().any(axis="columns").sum()),
    )
    return joined, part, _repeated(lookup_keys, pairs, lookup.part.uri, len(matched) - matched.nunique())


def _key_text(frame: pd.DataFrame, names: list[str]) -> pd.DataFrame:
    """The key columns as text with outer spaces trimmed, named by their place in `on`; an empty cell is missing."""
    text = pd.DataFrame({number: frame[name].astype("string").str.strip() for number, name in enumerate(names)})
    return text.replace("", pd.NA).set_axis([f"key{number}" for number in range(len(names))], axis="columns")


def _pairs(main_keys: pd.DataFrame, lookup_keys: pd.DataFrame, how: How) -> pd.DataFrame:
    """The row numbers of the main rows and the lookup rows whose keys are equal, as `how` keeps them, in order."""
    matching = " AND ".join(f"m.{name} = l.{name}" for name in main_keys.columns)
    sql = (
        f"SELECT coalesce(m.{_POSITION}, {_NONE}) AS {_MAIN}, coalesce(l.{_POSITION}, {_NONE}) AS {_LOOKUP} "  # noqa: S608 -- names of this module
        f"FROM main_keys m {how.value.upper()} JOIN lookup_keys l ON {matching} "
        f"ORDER BY m.{_POSITION} NULLS LAST, l.{_POSITION}"
    )
    with duckdb.connect() as connection:
        connection.register("main_keys", main_keys.assign(**{_POSITION: range(len(main_keys))}))
        connection.register("lookup_keys", lookup_keys.assign(**{_POSITION: range(len(lookup_keys))}))
        return connection.execute(sql).df()


def _taken(frame: pd.DataFrame, rows: pd.Series) -> pd.DataFrame:
    """The rows of `frame` at the numbers `rows`, in order; -1 is a row of empty cells, where ints stay whole."""
    if (rows == _NONE).any():
        whole = [name for name, dtype in frame.dtypes.items() if pd.api.types.is_integer_dtype(dtype)]
        frame = frame.astype(dict.fromkeys(whole, "Int64"))
    return frame.reset_index(drop=True).reindex(rows.to_numpy()).reset_index(drop=True)


def _main_side(table: pd.DataFrame, lookup: pd.DataFrame, pairs: pd.DataFrame, keys: list[Key]) -> pd.DataFrame:
    """The main columns of the joined rows; a row with no main row takes its keys from the lookup."""
    main = _taken(table, pairs[_MAIN])
    alone = (pairs[_MAIN] == _NONE).to_numpy()
    if alone.any():
        lookup_keys = _taken(lookup[[key.lookup for key in keys]], pairs[_LOOKUP])
        for key in keys:
            main[key.main] = main[key.main].where(~alone, lookup_keys[key.lookup])
    return main


def _lookup_side(table: pd.DataFrame, lookup: _Lookup, pairs: pd.DataFrame, keys: list[Key]) -> pd.DataFrame:
    """The lookup columns of the joined rows but its keys; a name the table has gets the suffix of the lookup."""
    added = _taken(lookup.frame.drop(columns=[key.lookup for key in keys]), pairs[_LOOKUP])
    taken = column_names(table)
    names: list[str] = []
    for name in column_names(added):
        names.append(values.unique(f"{name}_{lookup.suffix}", taken) if name in taken else name)
        taken.append(names[-1])
    return added.set_axis(names, axis="columns")


def _repeated(lookup_keys: pd.DataFrame, pairs: pd.DataFrame, uri: str, added: int) -> list[str]:
    """The warning about the lookup keys that matched a main row more than once, when they added rows."""
    if not added:
        return []
    matched = pairs[_LOOKUP][pairs[_MAIN] != _NONE].unique()
    keys = lookup_keys.iloc[sorted(matched)]
    repeated = [_shown(row) for row in keys[keys.duplicated()].drop_duplicates().itertuples(index=False)]
    named = settings().warnings.repeated_keys_named
    more = f" and {len(repeated) - named} more" if len(repeated) > named else ""
    return [
        f"The lookup '{uri}' matched main rows more than once, at the repeated keys: "
        f"{', '.join(repeated[:named])}{more}; {added} rows added."
    ]


def _shown(key: tuple[str, ...]) -> str:
    """A key as the warning names it: its one value, or its values in brackets."""
    return key[0] if len(key) == 1 else f"({', '.join(key)})"
