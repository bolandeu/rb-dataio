from __future__ import annotations

import typer

from .. import output
from ..core.dataio import api


def _render(data: dict) -> None:
    for entry in data["formats"]:
        abilities = [ability for ability in ("read", "write", "append") if entry[ability]]
        options = ", ".join(entry["options"]) or "none"
        output.human.echo(
            f"{entry['name']}  {' '.join(entry['extensions'])}  {'/'.join(abilities)}  options: {options}"
        )


@output.guard
def formats(
    ctx: typer.Context,
    json_output: bool = output.JsonOption,
    quiet: bool = output.QuietOption,
) -> None:
    """List every format: its extensions, whether it can read, write and append, and its options.

    Example: {cli} formats --json
    """
    output.emit_success(ctx, {"formats": [entry.to_dict() for entry in api.formats()]}, render_human=_render)
