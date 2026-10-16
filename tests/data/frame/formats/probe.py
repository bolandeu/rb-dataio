"""A format module that tests/test_frame.py adds to the formats package: it reads, it cannot write."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from rb_dataio.core.dataio.options import ReadOptions
from rb_dataio.formats import FormatAdapter, Loaded


class ProbeAdapter(FormatAdapter):
    name = "probe"
    extensions = (".probe",)
    options = ()

    def read(self, path: Path, options: ReadOptions) -> Loaded:
        return Loaded(pd.DataFrame({"probe": ["ok"]}))


ADAPTER = ProbeAdapter()
