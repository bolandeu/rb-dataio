"""http(s): a table read straight from a link, over the template's HttpProvider; read only.

The text format comes from `format=`, else from the URL (its extension, or the `output=` of a Google
'Publish to web' link), else from the Content-Type of the response. The body is then read by that
text format, with the encoding and delimiter detection of a file; a redirect is followed.
`WebProvider` makes the requests; a test sets its `transport`.
"""

from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import parse_qs, urlsplit

from ..core.dataio.address import Address
from ..core.dataio.options import ReadOptions
from ..core.errors import FormatUnsupported
from ..providers.base import Health
from ..providers.http import HttpProvider
from . import Loaded, RemoteAdapter, TextAdapter, adapters

MEDIA_TYPES = {
    "text/csv": "csv",
    "text/tab-separated-values": "tsv",
    "application/json": "json",
    "application/x-ndjson": "jsonl",
}


class WebProvider(HttpProvider):
    """Fetches the links of http(s) sources; a public link has no credential to check."""

    name = "web"
    credential_fields = ()
    required = False

    def health_check(self) -> Health:
        return Health(message="no credential: public links only")

    def fetch(self, url: str) -> tuple[bytes, str]:
        """The body of the response to a GET of `url`, and its media type."""
        response = self.request("GET", url, follow_redirects=True)
        return response.content, response.headers.get("Content-Type", "").split(";")[0].strip().lower()


def _text_format(**by: str) -> TextAdapter | None:
    """The text format whose name is `name`, or one of whose extensions is `suffix`."""
    for adapter in adapters():
        if isinstance(adapter, TextAdapter) and (
            adapter.name == by.get("name") or (by.get("suffix") and by["suffix"] in adapter.extensions)
        ):
            return adapter
    return None


def _format_of_url(address: Address) -> TextAdapter | None:
    url = urlsplit(address.place)
    output = next(iter(parse_qs(url.query).get("output", [])), "")
    return _text_format(suffix=PurePosixPath(url.path).suffix.lower()) or _text_format(name=output)


class HttpAdapter(RemoteAdapter):
    name = "http"
    schemes = ("http", "https")
    options = ("encoding", "sep")
    read_only = "http(s) is read only"

    def read_address(self, address: Address, options: ReadOptions) -> Loaded:
        named = _text_format(name=options.format) if options.format else None
        body, media_type = WebProvider().fetch(address.place)
        text_format = named or _format_of_url(address) or _text_format(name=MEDIA_TYPES.get(media_type, ""))
        if text_format is None:
            raise FormatUnsupported(
                f"'{address.text}': the format of the link is unknown (Content-Type '{media_type}').",
                action="Pass format=, or use a link that ends in .csv or .json.",
            )
        return text_format.load(body, options)


ADAPTER = HttpAdapter()
