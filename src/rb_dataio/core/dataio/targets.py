"""The targets seam of the write pipeline: a target address that is a template (`out/{region}.csv`, `out/part_{n}.csv`).

`is_template` answers whether a target is one; it says "no" until the split is built. `write_many` writes the
frame to the targets the template names and returns the report with `targets`, like `pipeline.write_frame`.
"""

from __future__ import annotations

import pandas as pd

from .options import WriteOptions
from .report import Report


def is_template(target: str, options: WriteOptions) -> bool:
    return False


def write_many(frame: pd.DataFrame, target: str, options: WriteOptions) -> Report:
    raise NotImplementedError("splitting a table into many targets is not built yet")
