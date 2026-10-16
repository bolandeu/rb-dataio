"""Containers: the part of a file or a service with named parts (sheets, tables) that a read or a write takes.

The part is the one the address or `sheet=` / `table=` names, else the first (a format with `part_required`
and several parts gives PartNotFound, which lists them); a write to a
new file makes the format's `first_part`. `*` reads every part, stacked with the column
`_sheet` that names the part of each row; parts with other columns give their union and a warning.
The location is a file or the `Remote` place of a service; `existing_parts` has none for a file
that does not exist yet.
"""

from __future__ import annotations

from pathlib import Path

from ...formats import ContainerAdapter, Loaded, Location
from ..errors import PartNotFound
from . import values
from .options import ReadOptions

ALL_PARTS = "*"
PART_COLUMN = "_sheet"


def read(
    adapter: ContainerAdapter[Location], location: Location, named: str | None, options: ReadOptions, uri: str
) -> Loaded:
    """The named part, the first when none is named, or every part stacked under `*`."""
    parts = adapter.parts(location)
    if named == ALL_PARTS:
        return _stacked(adapter, location, parts, options)
    if named is None and adapter.part_required and len(parts) > 1:
        raise PartNotFound(uri, "", parts)
    part = named if named is not None else next(iter(parts), "")
    if part not in parts:
        raise PartNotFound(uri, part, parts)
    return adapter.read_part(location, part, options)


def existing_parts(adapter: ContainerAdapter[Location], location: Location) -> list[str]:
    """The parts there are now: none in a file that does not exist yet."""
    return [] if isinstance(location, Path) and not location.exists() else adapter.parts(location)


def part_to_write(adapter: ContainerAdapter[Location], location: Location, named: str | None) -> str:
    """The named part, else the first there is, else the part a new file gets."""
    if named is not None:
        return named
    parts = existing_parts(adapter, location)
    return parts[0] if parts else adapter.first_part


def _stacked(adapter: ContainerAdapter[Location], location: Location, parts: list[str], options: ReadOptions) -> Loaded:
    loaded = [adapter.read_part(location, part, options) for part in parts]
    frames = [table.frame.copy() for table in loaded]
    for part, frame in zip(parts, frames, strict=True):
        frame.insert(0, PART_COLUMN, part)
    stacked = values.stack(frames)
    differing = [str(column) for column in stacked.columns if not all(column in frame for frame in frames)]
    warnings = (
        (f"the parts have different columns: {', '.join(differing)}; a part without one leaves it empty",)
        if differing
        else ()
    )
    return Loaded(stacked, infers_types=all(table.infers_types for table in loaded), warnings=warnings)
