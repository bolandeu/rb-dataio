"""The `restore` command: bring a target back from a backup, behind confirmation."""

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
    """Bring a target back from a backup (the newest without ID); what it holds now is backed up first.

    It replaces the target, so it asks first: --confirm skips the question.
    With --dry-run the report shows the target before and after, and nothing changes.

    Example: {cli} restore --dry-run --json
    """
    dry_run = output.is_dry_run(ctx)
    if not dry_run:
        output.require_confirmation(ctx, f"Restore backup {id or '(the newest)'} over its target", confirm)
    output.emit_success(ctx, api.restore(id, dry_run=dry_run).to_dict(), render_human=render_report)
