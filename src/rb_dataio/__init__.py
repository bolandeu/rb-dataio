"""dataio: read any source into a pandas DataFrame and write a DataFrame to any target.

    df = read("phrases.csv")
    report = write(df, "out.csv")
    report = convert("a.csv", "b.csv")

Every failure is a `DataioError` with `code`, `message` and `action`.
"""

from __future__ import annotations

from .core.dataio.api import backups, convert, formats, info, read, restore, write
from .core.errors import DataioError

__all__ = ["DataioError", "backups", "convert", "formats", "info", "read", "restore", "write"]
