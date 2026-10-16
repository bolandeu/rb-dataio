from __future__ import annotations

import typer

from .. import output
from ..core.dataio import api


def _render(data: dict) -> None:
    if not data["backups"]:
        output.human.echo("No backups.")
    for entry in data["backups"]:
        output.human.echo(f"{entry['id']}  {entry['time']}  {entry['target']}  {entry['rows']} rows")


@output.guard
def backups(
    ctx: typer.Context,
    json_output: bool = output.JsonOption,
    quiet: bool = output.QuietOption,
) -> None:
    """List the kept backups, newest first: id, time, target and rows.

    Example: {cli} backups --json
    """
    output.emit_success(ctx, {"backups": [entry.to_dict() for entry in api.backups()]}, render_human=_render)
