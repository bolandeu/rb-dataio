"""The batch seam of `convert`: many sources to many targets, one to one (`convert 'in/*.csv' 'out/{stem}.xlsx'`).

`converts_each` answers whether a convert is such a run: a source mask (a local path with `*`, `?` or `[`) and a
target with `{stem}`. `convert_each` runs it and returns the report with `targets` and, for `keep_going`, `errors`.
Each source is read and written alone, so each replaced target has its own backup; without `keep_going` the first
error stops the run and is raised. A dry run lists every target as a `PlannedBatchTarget` and writes nothing.
"""

from __future__ import annotations

import glob
import re
from pathlib import Path

from ..errors import DataioError, SourceNotFound
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
    done: list[BatchTarget] = []
    errors: list[BatchError] = []
    for each in sources:
        try:
            done.append(_convert_one(each, target.replace("{stem}", Path(each).stem), read_options, write_options))
        except DataioError as error:
            if not write_options.keep_going:
                raise
            errors.append(BatchError(uri=each, code=error.code, message=error.message))
    return Report(targets=done, errors=errors or None)


def _convert_one(source: str, target: str, read_options: ReadOptions, write_options: WriteOptions) -> BatchTarget:
    pipeline.refuse_over_source(source, target, write_options)
    frame, _, _ = pipeline.read_frame(source, read_options)
    if not write_options.dry_run:
        Path(parse(target).path).parent.mkdir(parents=True, exist_ok=True)
    part = pipeline.write_frame(frame, target, write_options).target
    if isinstance(part, PlannedTarget):
        return PlannedBatchTarget(
            uri=target,
            rows=part.rows or 0,
            exists=part.exists,
            rows_before=part.rows_before,
            rows_after=part.rows_after,
        )
    return BatchTarget(uri=target, rows=len(frame))
