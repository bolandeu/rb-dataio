"""A test format of `.db` files that start with the signature `BETA` (_signed.py)."""

from __future__ import annotations

from ._signed import SignedAdapter


class BetaAdapter(SignedAdapter):
    name = "beta"
    signature = b"BETA\n"


ADAPTER = BetaAdapter()
