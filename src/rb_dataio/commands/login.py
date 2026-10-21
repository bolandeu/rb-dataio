"""`auth login` / `auth logout` — only in CLIs generated with credentials (include_auth).

`commands/auth.py` registers these into the `auth` group when this module
exists; `auth status` is there in every CLI (the Standard, Health).
"""

from __future__ import annotations

import typer

from .. import output, providers
from ..core.errors import InvalidArguments
from ..credentials import manager as credentials


def _key_file_fields(provider: str, path: str) -> dict[str, str]:
    """The fields `provider` declares, taken from its key file."""
    declared = next((cls.credential_fields for cls in providers.all_providers() if cls.name == provider), None)
    if declared is None:
        raise InvalidArguments(f"Unknown provider '{provider}': a key file is stored for a known provider only.")
    fields = credentials.read_key_file(path)
    if missing := [field for field in declared if field not in fields]:
        raise InvalidArguments(f"The key file '{path}' has no {', '.join(missing)}.")
    return {field: fields[field] for field in declared}


def _secret(ctx: typer.Context, provider: str, non_interactive: bool) -> str:
    """The API key from the environment, else asked for."""
    secret = credentials.read_secret_from_env(provider)
    if secret is None:
        if ctx.obj.get("non_interactive") or non_interactive:
            raise InvalidArguments(
                f"No credential found in environment for provider '{provider}' and --non-interactive was set."
            )
        secret = typer.prompt(f"Enter API key for '{provider}'", hide_input=True)
    return secret


@output.guard
def login(
    ctx: typer.Context,
    provider: str = typer.Option("default", "--provider", help="Provider/profile name."),
    key_file: str | None = typer.Option(
        None,
        "--credentials",
        help="Key file (JSON) to store the provider's fields from, e.g. a Google service-account key.",
    ),
    non_interactive: bool = output.NonInteractiveOption,
    json_output: bool = output.JsonOption,
    quiet: bool = output.QuietOption,
) -> None:
    """Store a credential for a provider; with --credentials, the fields of a key file.

    Example: {cli} auth login --provider google --credentials key.json
    """
    if key_file is not None:
        credentials.store_credential(provider, _key_file_fields(provider, key_file))
    else:
        credentials.store_secret(provider, _secret(ctx, provider, non_interactive))
    output.emit_success(
        ctx,
        {"provider": provider},
        render_human=lambda d: output.human.echo(f"Stored credential for '{d['provider']}'."),
    )


@output.guard
def logout(
    ctx: typer.Context,
    provider: str = typer.Option("default", "--provider", help="Provider/profile name."),
    json_output: bool = output.JsonOption,
    quiet: bool = output.QuietOption,
) -> None:
    """Remove a stored credential.

    Example: {cli} auth logout --provider default
    """
    credentials.delete_secret(provider)
    output.emit_success(
        ctx,
        {"provider": provider},
        render_human=lambda d: output.human.echo(f"Removed credential for '{d['provider']}'."),
    )
