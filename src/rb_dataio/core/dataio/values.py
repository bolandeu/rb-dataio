"""Value normalisation: the one step every read goes through after its adapter.

A pass-through for now. NA words, empty cells, type inference with the leading-zero
rule, `as_text`, `dtypes` and header repair come here with the CSV/values task.
"""

from __future__ import annotations

import pandas as pd

from .options import ReadOptions


def normalise(frame: pd.DataFrame, options: ReadOptions) -> pd.DataFrame:
    return frame
