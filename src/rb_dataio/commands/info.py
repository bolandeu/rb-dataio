from __future__ import annotations

import typer

from .. import output
from ..core.dataio import api
from ._parameters import option, pairs


def _render(described: dict) -> None:
    output.human.key_values("Source", described["source"])
    output.human.key_values("Types", described["types"])
    output.human.echo(f"Preview ({len(described['preview'])} rows):")
    for row in described["preview"]:
        output.human.echo(f"  {row}")


@output.guard
def info(
    ctx: typer.Context,
    source: str = typer.Argument(..., help="Address of the source, e.g. a.csv or book.xlsx#Sheet1."),
    format: str | None = option("format", None),
    sheet: str | None = option("sheet", None),
    table: str | None = option("table", None),
    encoding: str | None = option("encoding", None),
    sep: str | None = option("sep", None),
    header: bool = option("header", True),
    as_text: bool = option("as_text", False),
    dtypes: list[str] | None = option("dtypes", None, metavar="COLUMN=TYPE"),
    limit: int | None = option("limit", None, min=0),
    json_output: bool = output.JsonOption,
    quiet: bool = output.QuietOption,
) -> None:
    """Describe a source: format, encoding, delimiter, rows, column types and the first 5 rows.

    Example: {cli} info a.csv --json
    """
    described = api.info(
        source,
        format=format,
        sheet=sheet,
        table=table,
        encoding=encoding,
        sep=sep,
        header=header,
        as_text=as_text,
        dtypes=pairs(dtypes),
        limit=limit,
    )
    output.emit_success(ctx, described.to_dict(), render_human=_render)
