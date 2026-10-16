"""The format registry: the adapter of an address, the text format of data with no file, the formats list.

`resolve` picks the adapter of an address by `format=` or the extension; `text_adapter` picks a
text format by name for stdin, stdout and the in-memory text of `write()` (`text` is txt).
"""

from __future__ import annotations

from collections.abc import Sequence

# `from ...formats import` and not `from ... import formats`: the package root's
# `formats` is the public function, which hides the subpackage of the same name.
from ...formats import FormatAdapter, TextAdapter, adapters
from ...formats import txt as txt_format
from ..errors import FormatUnknown
from .address import Address
from .report import FormatInfo

TEXT = "text"  # the in-memory name of txt: a string read as text, a table written one value per line


def resolve(address: Address, format_name: str | None) -> FormatAdapter:
    """The adapter named by `format=`, else the one of the address's extension."""
    known = adapters()
    for adapter in known:
        if (adapter.name == format_name) if format_name else (address.suffix in adapter.extensions):
            return adapter
    raise FormatUnknown(address.text, [adapter.name for adapter in known])


def text_adapter(format_name: str, uri: str, *, also: Sequence[str] = ()) -> TextAdapter:
    """The text format named `format_name` (`text` is txt), for data with no file: stdin, stdout, memory.

    `also` are the other names the caller takes, listed when the name is unknown.
    """
    wanted = txt_format.ADAPTER.name if format_name == TEXT else format_name
    known = [adapter for adapter in adapters() if isinstance(adapter, TextAdapter)]
    for adapter in known:
        if adapter.name == wanted:
            return adapter
    raise FormatUnknown(uri, [*also, TEXT, *(adapter.name for adapter in known)])


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
