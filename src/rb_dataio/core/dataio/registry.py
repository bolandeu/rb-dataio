"""The format registry: the adapter for an address, and the list `formats()` returns."""

from __future__ import annotations

# `from ...formats import` and not `from ... import formats`: the package root's
# `formats` is the public function, which hides the subpackage of the same name.
from ...formats import FormatAdapter, adapters
from ..errors import FormatUnknown
from .address import Address
from .report import FormatInfo


def resolve(address: Address, format_name: str | None) -> FormatAdapter:
    """The adapter named by `format=`, else the one of the address's extension."""
    known = adapters()
    for adapter in known:
        if (adapter.name == format_name) if format_name else (address.suffix in adapter.extensions):
            return adapter
    raise FormatUnknown(address.text, [adapter.name for adapter in known])


def describe() -> list[FormatInfo]:
    return [
        FormatInfo(
            name=adapter.name,
            extensions=list(adapter.extensions),
            read=adapter.reads,
            write=adapter.writes,
            append=adapter.appends,
            options=list(adapter.options),
        )
        for adapter in adapters()
    ]
