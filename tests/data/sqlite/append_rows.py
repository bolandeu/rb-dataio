"""A process of the concurrency test: append 1000 rows tagged with its name to table t of a base; print WRITE_FAILED if refused."""

from __future__ import annotations

import sys

import pandas as pd

from rb_dataio import DataioError, write

base, tag = sys.argv[1], sys.argv[2]
frame = pd.DataFrame({"phrase": [f"{tag}-{number}" for number in range(1000)], "freq": range(1000)})
try:
    write(frame, f"{base}#t", mode="append")
except DataioError as exc:
    print(exc.code)
