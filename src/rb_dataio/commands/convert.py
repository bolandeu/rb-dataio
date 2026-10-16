"""The `convert` command: read a source, write a target, report both sides.

It maps the flags to one `convert()` call. The options both sides have take
`--in-` / `--out-`; `--query` is of the source, `--start` and `--value-input` of the target.
A replace that needs confirmation (a target that is the source itself, a part with rows
of a remote container) asks first (`--confirm` skips the question). With the target `-` stdout is the data:
the human report is left out, and under `--json` the data is records inside the
envelope. `render_report` is the human view of a report, shared with `restore`.
"""

from __future__ import annotations

import typer
from rich.markup import escape

from .. import output
from ..core.dataio import api
from ..core.dataio.address import STDIO_TEXT
from ..core.dataio.objects import RECORDS
from ..core.dataio.options import Mode, ValueInput
from ..core.dataio.report import Report
from ..core.errors import ConfirmationRequired
from ._parameters import option, pairs


def render_report(report: dict) -> None:
    for side in ("source", "backup", "target"):
        if side in report:
            output.human.key_values(side.capitalize(), report[side])
    render_warnings(report)


def render_warnings(report: dict) -> None:
    for warning in report["warnings"]:
        output.human.err_console.print(f"[yellow]Warning:[/yellow] {escape(warning)}")


@output.guard
def convert(
    ctx: typer.Context,
    source: str = typer.Argument(
        ..., help="Address of the source, e.g. a.csv, book.xlsx#Sheet1, gsheet://ID#Sheet1 or an https URL; - is stdin."
    ),
    target: str = typer.Argument(..., help="Address of the target, e.g. b.csv or gsheet://ID#Sheet1; - is stdout."),
    in_format: str | None = option("format", None, "in"),
    in_sheet: str | None = option("sheet", None, "in"),
    in_table: str | None = option("table", None, "in"),
    in_encoding: str | None = option("encoding", None, "in"),
    in_sep: str | None = option("sep", None, "in"),
    in_header: bool = option("header", True, "in"),
    in_credentials: str | None = option("credentials", None, "in"),
    as_text: bool = option("as_text", False),
    dtypes: list[str] | None = option("dtypes", None, metavar="COLUMN=TYPE"),
    limit: int | None = option("limit", None, min=0),
    query: str | None = option("query", None),
    out_format: str | None = option("format", None, "out"),
    out_sheet: str | None = option("sheet", None, "out"),
    out_table: str | None = option("table", None, "out"),
    out_encoding: str | None = option("encoding", None, "out"),
    out_sep: str | None = option("sep", None, "out"),
    out_header: bool = option("header", True, "out"),
    out_credentials: str | None = option("credentials", None, "out"),
    mode: Mode = option("mode", Mode.REPLACE),
    start: str | None = option("start", None),
    value_input: ValueInput = option("value_input", ValueInput.RAW),
    profile: str | None = option("profile", None),
    overwrite: bool = option("overwrite", False),
    backup: bool = option("backup", True),
    dry_run: bool = output.DryRunOption,
    confirm: bool = output.ConfirmOption,
    json_output: bool = output.JsonOption,
    quiet: bool = output.QuietOption,
) -> None:
    """Read a table from SOURCE and write it to TARGET; report both sides.

    Options both sides have take --in- (the source) or --out- (the target).
    --query is SQL over the source whose result is written: inside a base
    it names its tables, over any other source the table is data.
    With --dry-run the report comes back and nothing is written.
    A TARGET that is the SOURCE itself, or a sheet with rows of a Google
    spreadsheet that the write replaces, asks first: --confirm skips the question.
    --start and --value-input place and pass the values in a sheet of a service.
    SOURCE - is stdin, its format comes from the content; TARGET - is stdout:
    CSV, one value per line for one column, or --out-format; under --json the
    data is inside the envelope as data.

    Example: {cli} convert a.csv b.csv --json
    """
    to_stdout = target == STDIO_TEXT
    if to_stdout and ctx.obj.get("json"):
        out_format = RECORDS  # stdout stays one JSON document: the data rides in the envelope

    def run(overwrite: bool) -> Report:
        return api.convert(
            source,
            target,
            in_format=in_format,
            in_sheet=in_sheet,
            in_table=in_table,
            in_encoding=in_encoding,
            in_sep=in_sep,
            in_header=in_header,
            in_credentials=in_credentials,
            as_text=as_text,
            dtypes=pairs(dtypes),
            limit=limit,
            query=query,
            out_format=out_format,
            out_sheet=out_sheet,
            out_table=out_table,
            out_encoding=out_encoding,
            out_sep=out_sep,
            out_header=out_header,
            out_credentials=out_credentials,
            mode=mode,
            start=start,
            value_input=value_input,
            profile=profile,
            overwrite=overwrite,
            backup=backup,
            dry_run=output.is_dry_run(ctx),
        )

    try:
        report = run(overwrite or confirm)
    except ConfirmationRequired as needed:
        output.require_confirmation(ctx, needed.question, confirm)
        report = run(True)
    output.emit_success(ctx, report.to_dict(), render_human=render_warnings if to_stdout else render_report)
