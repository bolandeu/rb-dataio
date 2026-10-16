"""The `restore` command: bring a target back from a backup.

A stub until the protection task: the library refuses with `NOT_AVAILABLE`.
The command is registered now so that the CLI surface does not change later.
"""

from __future__ import annotations

import typer

from .. import output
from ..core.dataio import api
from .convert import render_report


@output.guard
def restore(
    ctx: typer.Context,
    id: str | None = typer.Argument(None, help="Backup id from the backups command; the newest when left out."),
    dry_run: bool = output.DryRunOption,
    confirm: bool = output.ConfirmOption,
    json_output: bool = output.JsonOption,
    quiet: bool = output.QuietOption,
) -> None:
    """Bring a target back from a backup. Not available in this release yet.

    Example: {cli} restore --dry-run --json
    """
    output.emit_success(ctx, api.restore(id).to_dict(), render_human=render_report)
