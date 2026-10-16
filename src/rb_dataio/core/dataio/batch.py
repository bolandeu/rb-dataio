"""The batch seam of `convert`: many sources to many targets, one to one (`convert 'in/*.csv' 'out/{stem}.xlsx'`).

`converts_each` answers whether a convert is such a run: a source mask (a local path with `*`, `?` or `[`) and a
target with `{stem}`. `convert_each` runs it and returns the report with `targets` and, for `keep_going`, `errors`.
Each source is read and written alone, so each replaced target has its own backup; without `keep_going` the first
error stops the run and is raised. Two sources whose targets are one (`a/x.csv`, `b/x.csv` for `{stem}`) are
INVALID_ARGUMENTS before anything is written. The warnings of the reads are in the report, each prefixed by its file. A dry run lists every target as a `PlannedBatchTarget` and writes nothing.
"""

from __future__ import annotations

import glob
import re
from pathlib import Path

from ..errors import DataioError, InvalidParameter, SourceNotFound
from . import pipeline
from .address import FILE, parse
from .options import ReadOptions, WriteOptions
from .report import BatchError, BatchTarget, PlannedBatchTarget, PlannedTarget, Report

STEM = "stem"
_MASK = re.compile(r"[*?\[]")


def converts_each(source: str, target: str) -> bool:
    return (
        "\n" not in source
        and parse(source).scheme == FILE
        and bool(_MASK.search(source))
        and STEM in parse(target).placeholders
    )


def convert_each(source: str, target: str, read_options: ReadOptions, write_options: WriteOptions) -> Report:
    sources = sorted(path for path in glob.glob(source, recursive=True) if Path(path).is_file())
    if not sources:
        raise SourceNotFound(source)
    pairs = [(each, target.replace("{" + STEM + "}", Path(each).stem)) for each in sources]
    _require_distinct(pairs)
    done: list[BatchTarget] = []
    errors: list[BatchError] = []
    warnings: list[str] = []
    for each, into in pairs:
        try:
            one, read_warnings = _convert_one(each, into, read_options, write_options)
        except DataioError as error:
            if not write_options.keep_going:
                raise
            errors.append(BatchError(uri=each, code=error.code, message=error.message))
            continue
        done.append(one)
        warnings.extend(f"{each}: {warning}" for warning in read_warnings)
    return Report(targets=done, errors=errors or None, warnings=warnings)


def _require_distinct(pairs: list[tuple[str, str]]) -> None:
    """INVALID_ARGUMENTS naming the sources that would be written to one target."""
    by_target: dict[str, list[str]] = {}
    for each, into in pairs:
        by_target.setdefault(into.casefold(), []).append(each)
    for into, names in by_target.items():
        if len(names) > 1:
            raise InvalidParameter(f"Sources {' and '.join(names)} get the same target '{into}': nothing is written.")


def _convert_one(
    source: str, target: str, read_options: ReadOptions, write_options: WriteOptions
) -> tuple[BatchTarget, list[str]]:
    """The target one source was written to and the warnings of its read."""
    pipeline.refuse_over_source(source, target, write_options)
    frame, _, read_warnings = pipeline.read_frame(source, read_options)
    if not write_options.dry_run:
        Path(parse(target).path).parent.mkdir(parents=True, exist_ok=True)
    part = pipeline.write_frame(frame, target, write_options).target
    if isinstance(part, PlannedTarget):
        planned = PlannedBatchTarget(
            uri=target,
            rows=part.rows or 0,
            exists=part.exists,
            rows_before=part.rows_before,
            rows_after=part.rows_after,
        )
        return planned, read_warnings
    return BatchTarget(uri=target, rows=len(frame)), read_warnings
