"""The `join` command: the main source with the columns of its lookups, written to a target.

It maps the flags to one `join()` call, as `convert` maps to `convert()`: the `--in-` options are of every
source, the `--out-` options and the others of the target. `--lookup` and `--on` repeat. A replace that needs
confirmation asks first (`--confirm` skips the question); with the target `-` stdout is the data. The human report
adds a line per lookup (matched, unmatched and empty keys); under `--json` the report has `lookups`.
"""

from __future__ import annotations

import typer

from .. import output
from ..core.dataio import api
from ..core.dataio.address import STDIO_TEXT
from ..core.dataio.objects import RECORDS
from ..core.dataio.options import How, Mode, ValueInput
from ..core.dataio.report import Report
from ..core.errors import ConfirmationRequired, LibraryAction
from ._parameters import names, option, renames
from .convert import render_report, render_warnings


def render_join_report(report: dict) -> None:
    render_report(report)
    for lookup in report["lookups"]:
        output.human.echo(
            f"Lookup {lookup['uri']}: {lookup['rows']} rows, {lookup['matched']} matched, "
            f"{lookup['unmatched']} unmatched, {lookup['empty_keys']} empty keys"
        )


@output.guard
def join(
    ctx: typer.Context,
    source: str = typer.Argument(..., help="Address of the main source, e.g. main.csv or book.xlsx#Sheet1."),
    target: str = typer.Argument(..., help="Address of the target, e.g. out.xlsx or gsheet://ID#Sheet1; - is stdout."),
    lookups: list[str] | None = option("lookups", None, None, "--lookup", metavar="ADDRESS"),
    on: list[str] | None = option("on", None, metavar="KEY"),
    how: How = option("how", How.LEFT),
    in_format: str | None = option("format", None, "in"),
    in_sheet: str | None = option("sheet", None, "in"),
    in_table: str | None = option("table", None, "in"),
    in_encoding: str | None = option("encoding", None, "in"),
    in_sep: str | None = option("sep", None, "in"),
    in_header: bool = option("header", True, "in"),
    in_credentials: str | None = option("credentials", None, "in"),
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
    columns: list[str] | None = option("columns", None, metavar="COLUMN"),
    rename: list[str] | None = option("rename", None, metavar="OLD=NEW"),
    overwrite: bool = option("overwrite", False),
    backup: bool = option("backup", True),
    dry_run: bool = output.DryRunOption,
    confirm: bool = output.ConfirmOption,
    json_output: bool = output.JsonOption,
    quiet: bool = output.QuietOption,
) -> None:
    """Join the columns of lookups to a main SOURCE by key columns and write it to TARGET.

    --lookup is the address of a lookup and repeats; --on names a key column, or
    main_name=lookup_name when the lookup calls it differently, and repeats for several keys.
    --how keeps every source row (left, the default), every lookup row (right, one
    lookup), the matched rows (inner) or all (full). Keys compare as text with outer
    spaces trimmed; an empty key matches nothing. A lookup column whose name the table
    has gets the suffix of the lookup. The report lists each lookup's rows, matched,
    unmatched and empty keys. The --in- options are of every source, the --out- options
    and the others of the target, as in convert. With --dry-run the report comes back and
    nothing is written. A TARGET that is the SOURCE or a lookup, or a sheet with rows of a
    Google spreadsheet that the write replaces, asks first: --confirm skips the question.
    TARGET - is stdout, as in convert; under --json the data is inside the envelope as data.

    Example: {cli} join main.csv out.xlsx --lookup prices.xlsx#Prices --on sku --on region --how left
    """
    to_stdout = target == STDIO_TEXT
    if to_stdout and ctx.obj.get("json"):
        out_format = RECORDS  # stdout stays one JSON document: the data rides in the envelope

    def run(overwrite: bool) -> Report:
        return api.join(
            source,
            target,
            lookups=[*lookups] if lookups else None,  # a copy: list[Source] is invariant
            on=on,
            how=how,
            in_format=in_format,
            in_sheet=in_sheet,
            in_table=in_table,
            in_encoding=in_encoding,
            in_sep=in_sep,
            in_header=in_header,
            in_credentials=in_credentials,
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
            columns=names(columns),
            rename=renames(rename),
            overwrite=overwrite,
            backup=backup,
            dry_run=output.is_dry_run(ctx),
        )

    try:
        try:
            report = run(overwrite or confirm)
        except ConfirmationRequired as needed:
            output.require_confirmation(ctx, needed.question, confirm)
            report = run(True)
    except LibraryAction as error:
        raise error.for_cli() from error
    output.emit_success(ctx, report.to_dict(), render_warnings if to_stdout else render_join_report)
