"""A test format of `.db` files that start with the signature `ALPHA` (_signed.py)."""

from __future__ import annotations

from ._signed import SignedAdapter


class AlphaAdapter(SignedAdapter):
    name = "alpha"
    signature = b"ALPHA\n"


ADAPTER = AlphaAdapter()
