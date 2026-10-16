"""The sources seam of the read pipeline: an address that names many sources (a mask, a folder, a list).

`names_many` answers whether a source names many; it says "no" until the merge is built. `read_many` reads
them as one table, like `pipeline.read_frame`: the table, the source part of the report and the warnings.
"""

from __future__ import annotations

import pandas as pd

from .options import ReadOptions
from .report import SourcePart


def names_many(source: object, options: ReadOptions) -> bool:
    return False


def read_many(source: object, options: ReadOptions) -> tuple[pd.DataFrame, SourcePart, list[str]]:
    raise NotImplementedError("merging many sources is not built yet")
