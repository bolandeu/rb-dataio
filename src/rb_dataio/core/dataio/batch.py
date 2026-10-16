"""The batch seam of `convert`: many sources to many targets, one to one (`convert 'in/*.csv' 'out/{stem}.xlsx'`).

`converts_each` answers whether a convert is such a run; it says "no" until the batch convert is built.
`convert_each` runs it and returns the report with `targets` and, for `keep_going`, `errors`.
"""

from __future__ import annotations

from .options import ReadOptions, WriteOptions
from .report import Report


def converts_each(source: str, target: str) -> bool:
    return False


def convert_each(source: str, target: str, read_options: ReadOptions, write_options: WriteOptions) -> Report:
    raise NotImplementedError("converting many files one to one is not built yet")
