"""The `convert` command: read a source, write a target, report both sides.

It maps the flags to one `convert()` call. The options both sides have take
`--in-` / `--out-`. `render_report` is the human view of a report, shared with `restore`.
"""

from __future__ import annotations

import typer
from rich.markup import escape

from .. import output
from ..core.dataio import api
from ..core.dataio.options import Mode
from ._parameters import option, pairs


def render_report(report: dict) -> None:
    for side in ("source", "target"):
        if side in report:
            output.human.key_values(side.capitalize(), report[side])
    for warning in report["warnings"]:
        output.human.err_console.print(f"[yellow]Warning:[/yellow] {escape(warning)}")


@output.guard
def convert(
    ctx: typer.Context,
    source: str = typer.Argument(..., help="Address of the source, e.g. a.csv or book.xlsx#Sheet1."),
    target: str = typer.Argument(..., help="Address of the target, e.g. b.csv."),
    in_format: str | None = option("format", None, "in"),
    in_sheet: str | None = option("sheet", None, "in"),
    in_table: str | None = option("table", None, "in"),
    in_encoding: str | None = option("encoding", None, "in"),
    in_sep: str | None = option("sep", None, "in"),
    in_header: bool = option("header", True, "in"),
    as_text: bool = option("as_text", False),
    dtypes: list[str] | None = option("dtypes", None, metavar="COLUMN=TYPE"),
    limit: int | None = option("limit", None, min=0),
    out_format: str | None = option("format", None, "out"),
    out_sheet: str | None = option("sheet", None, "out"),
    out_table: str | None = option("table", None, "out"),
    out_encoding: str | None = option("encoding", None, "out"),
    out_sep: str | None = option("sep", None, "out"),
    out_header: bool = option("header", True, "out"),
    mode: Mode = option("mode", Mode.REPLACE),
    profile: str | None = option("profile", None),
    overwrite: bool = option("overwrite", False),
    backup: bool = option("backup", True),
    dry_run: bool = output.DryRunOption,
    json_output: bool = output.JsonOption,
    quiet: bool = output.QuietOption,
) -> None:
    """Read a table from SOURCE and write it to TARGET; report both sides.

    Options both sides have take --in- (the source) or --out- (the target).
    With --dry-run the report comes back and nothing is written.

    Example: {cli} convert a.csv b.csv --json
    """
    report = api.convert(
        source,
        target,
        in_format=in_format,
        in_sheet=in_sheet,
        in_table=in_table,
        in_encoding=in_encoding,
        in_sep=in_sep,
        in_header=in_header,
        as_text=as_text,
        dtypes=pairs(dtypes),
        limit=limit,
        out_format=out_format,
        out_sheet=out_sheet,
        out_table=out_table,
        out_encoding=out_encoding,
        out_sep=out_sep,
        out_header=out_header,
        mode=mode,
        profile=profile,
        overwrite=overwrite,
        backup=backup,
        dry_run=output.is_dry_run(ctx),
    )
    output.emit_success(ctx, report.to_dict(), render_human=render_report)
