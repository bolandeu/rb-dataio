"""The `info` command: a description of a source before a read.

It takes the read options of `read()` and maps them to one `info()` call.
"""

from __future__ import annotations

import typer

from .. import output
from ..core.dataio import api
from ..core.dataio.options import SOURCE_COLUMN
from ..core.errors import LibraryAction
from ._parameters import option, pairs


def _render(described: dict) -> None:
    output.human.key_values("Source", described["source"])
    output.human.key_values("Types", described["types"])
    if described["part_rows"]:
        output.human.key_values("Tables", described["part_rows"])
    elif described["parts"]:
        output.human.echo(f"Parts: {', '.join(described['parts'])}")
    output.human.echo(f"Preview ({len(described['preview'])} rows):")
    for row in described["preview"]:
        output.human.echo(f"  {row}")


@output.guard
def info(
    ctx: typer.Context,
    source: str = typer.Argument(
        ..., help="Address of the source, e.g. a.csv, book.xlsx#Sheet1, gsheet://ID#Sheet1 or an https URL."
    ),
    format: str | None = option("format", None),
    sheet: str | None = option("sheet", None),
    table: str | None = option("table", None),
    encoding: str | None = option("encoding", None),
    sep: str | None = option("sep", None),
    header: bool = option("header", True),
    credentials: str | None = option("credentials", None),
    as_text: bool = option("as_text", False),
    dtypes: list[str] | None = option("dtypes", None, metavar="COLUMN=TYPE"),
    limit: int | None = option("limit", None, min=0),
    query: str | None = option("query", None),
    source_column: str | None = option("source_column", SOURCE_COLUMN),
    strict: bool = option("strict", False),
    json_output: bool = output.JsonOption,
    quiet: bool = output.QuietOption,
) -> None:
    """Describe a source: format, encoding, delimiter, rows, column types, the first 5 rows, the sheets or tables.

    With --query it describes the result of the SQL: inside a base it names
    its tables, over any other source the table is data. A Google spreadsheet
    lists its sheets; an address of many sources is described as the merged table
    (--source-column, --strict, which fails with SCHEMA_MISMATCH); --credentials is the key file to reach it with.

    Example: {cli} info a.csv --json
    """
    try:
        described = api.info(
            source,
            format=format,
            sheet=sheet,
            table=table,
            encoding=encoding,
            sep=sep,
            header=header,
            credentials=credentials,
            as_text=as_text,
            dtypes=pairs(dtypes),
            limit=limit,
            query=query,
            source_column=source_column,
            strict=strict,
        )
    except LibraryAction as error:
        raise error.for_cli() from error
    output.emit_success(ctx, described.to_dict(), render_human=_render)
