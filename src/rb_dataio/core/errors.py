"""The expected failures of the CLI and the library: one `CliError` subclass per code.

Each error has a code, a message, an action and an exit code; `output.guard`
puts it in the error envelope. `DataioError` is the family of read and write failures,
the protection of a target among them: a replace that needs confirmation (`ConfirmationRequired`:
a write over the source, `WriteOverSource`, or the replace of a non-empty part, `NonEmptyPartReplace`)
and a backup that is not kept (`BackupNotFound`). A Google spreadsheet the service account may not
open or change is `SheetNotShared`, which names the email to share it with. A key file that cannot be read is `KeyFileUnreadable`. A file of sheets or tables without the
named one is `PartNotFound`, with the parts it has in the action. Sources merged with `strict=True` that
do not share their columns are `SchemaMismatch`, which lists the columns of each source. `SchemaMismatch` and
`TargetExists` are `LibraryAction`s: the action names a library argument, `for_cli()` words it as the CLI flag.
"""

from __future__ import annotations

from .._distribution import DIST_NAME
from .version import cli_name

# The real command (may differ from the package name) for `action` hints;
# `uv tool upgrade` takes the distribution name, which is the package's.
_CLI = cli_name()
_DIST = DIST_NAME

# Every exit code a generated CLI uses and what it means — the same table in
# conventions.md, and `describe --json`'s `exitCodes`. tests/test_describe.py
# fails when a CliError below uses a code that isn't listed here.
EXIT_CODES: dict[int, str] = {
    0: "Success",
    1: "General error (incl. UNEXPECTED and ABORTED)",
    2: "Invalid arguments",
    3: "Authentication error",
    4: "Project not initialized",
    5: "Provider error (external service: network, timeout, 5xx, 429, bad body)",
    6: "CLI too old for this project or database",
}


class CliError(Exception):
    """Base error for all expected, user-facing CLI failures.

    Every raise carries a stable `code`, a human `message`, an optional
    `action` telling the caller (human or agent) how to recover, and the
    process exit code to use. Only named, expected failure modes get a
    subclass here; anything else that escapes a command is turned into an
    `UNEXPECTED` envelope by `output.guard`, so `--json` callers always get
    JSON back.
    """

    def __init__(self, code: str, message: str, *, action: str | None = None, exit_code: int = 1) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.action = action
        self.exit_code = exit_code

    def to_dict(self) -> dict:
        payload: dict = {"code": self.code, "message": self.message}
        if self.action:
            payload["action"] = self.action
        return payload


class ProjectNotInitialized(CliError):
    def __init__(self, path: str) -> None:
        super().__init__(
            "PROJECT_NOT_INITIALIZED",
            f"No project found at or above '{path}'.",
            action=f"Run '{_CLI} init' in the project directory.",
            exit_code=4,
        )


class AuthRequired(CliError):
    """`login_options`: what `auth login` needs besides the provider, e.g. `--credentials <key.json>`."""

    def __init__(self, provider: str, *, login_options: str = "") -> None:
        super().__init__(
            "AUTH_REQUIRED",
            f"Authentication is required for provider '{provider}'.",
            action=f"Run '{_CLI} auth login --provider {provider}{f' {login_options}' if login_options else ''}'.",
            exit_code=3,
        )


class KeyFileUnreadable(CliError):
    """A key file named by a flag or an env var is missing or no JSON object of fields."""

    def __init__(self, path: str, reason: str) -> None:
        super().__init__(
            "AUTH_REQUIRED",
            f"The key file '{path}' cannot be read: {reason}",
            action="Pass the path of a key file (JSON) as the service gives it, e.g. a Google service-account key.",
            exit_code=3,
        )


class CredentialsUnhealthy(CliError):
    def __init__(self, problems: dict[str, str]) -> None:
        listed = ", ".join(f"{provider} ({status})" for provider, status in problems.items())
        super().__init__(
            "CREDENTIALS_UNHEALTHY",
            f"{len(problems)} credential(s) need attention: {listed}.",
            action=f"See each entry's `message`; store a credential with '{_CLI} auth login --provider <name>'.",
            exit_code=3,
        )


class DependencyTooOld(CliError):
    """Another CLI this one calls is missing or older than required (core/deps.py).

    `dist` is its distribution name — what `uv tool` knows it by (`rb-serp`
    for the `serp` command, standard §10). With `install_url` the action is a
    pinned, runnable install; without it, what to install and no fake URL.
    """

    def __init__(
        self,
        name: str,
        installed: str | None,
        required: str | None,
        *,
        install_url: str | None = None,
        dist: str | None = None,
    ) -> None:
        dist = dist or name
        found = "is not installed" if installed is None else f"is {installed}"
        need = f"{name} >= {required}" if required else name
        if install_url:
            repo = install_url.removesuffix(".git")
            tag = f"v{required}" if required else "<latest release tag>"
            action = f"Run 'uv tool install \"{dist} @ git+{repo}.git@{tag}\" --force', then retry."
        elif installed is not None:
            action = f"Run 'uv tool upgrade {dist}', then retry."
        else:
            action = f"Install {need} (distribution {dist}; see its README for the install command), then retry."
        super().__init__(
            "DEPENDENCY_TOO_OLD",
            f"'{name}' {found}; {_CLI} needs {need}.",
            action=action,
            exit_code=1,
        )


class InvalidArguments(CliError):
    def __init__(self, message: str) -> None:
        super().__init__("INVALID_ARGUMENTS", message, exit_code=2)


class CredentialStoreUnavailable(CliError):
    def __init__(self, provider: str, reason: str) -> None:
        super().__init__(
            "CREDENTIAL_STORE_UNAVAILABLE",
            f"Could not access the OS credential store for provider '{provider}': {reason}",
            action="Set the credential via an environment variable instead of 'auth login' (see 'auth login --help').",
            exit_code=1,
        )


class ProviderError(CliError):
    """An external service failed: network, timeout, HTTP 5xx/429, malformed response.

    `status` is the HTTP status when there was one. Raised by
    `providers.HttpProvider` after its retries are exhausted — commands and
    services normally don't construct this themselves.
    """

    def __init__(self, provider: str, message: str, *, status: int | None = None, action: str | None = None) -> None:
        super().__init__(
            "PROVIDER_ERROR",
            f"Provider '{provider}': {message}",
            action=action or "Retry later; if it keeps failing, check the provider's status page.",
            exit_code=5,
        )
        self.provider = provider
        self.status = status

    def to_dict(self) -> dict:
        payload = super().to_dict()
        payload["provider"] = self.provider
        if self.status is not None:
            payload["status"] = self.status
        return payload


class CliTooOld(CliError):
    def __init__(self, installed: str, required: str) -> None:
        super().__init__(
            "CLI_TOO_OLD",
            f"This project requires {_CLI} >= {required}, but {installed} is installed.",
            action=f"Run 'uv tool upgrade {_DIST}' (or lower cli.min_version in the project's config.toml).",
            exit_code=6,
        )


class Aborted(CliError):
    def __init__(self, description: str) -> None:
        super().__init__("ABORTED", f"{description}: aborted by user.", exit_code=1)


class DatabaseUnavailable(CliError):
    """`<TOOL>_DATABASE_URL` is set but unusable: unreachable, wrong credentials, not PostgreSQL (core/db.py).

    Exit 5 like any external service. Never answered by falling back to the
    local SQLite file — data written there would silently miss the shared base.
    """

    def __init__(self, message: str, *, action: str | None = None) -> None:
        super().__init__(
            "DATABASE_UNAVAILABLE",
            message,
            action=action or "Check the database URL and that the server is reachable; then retry.",
            exit_code=5,
        )


class DatabaseNotMigrated(CliError):
    """The shared database's schema is behind this CLI's migrations (core/db.py)."""

    def __init__(self, current: str | None, head: str) -> None:
        super().__init__(
            "DATABASE_NOT_MIGRATED",
            f"The database schema is at revision {current or 'none'}, this {_CLI} needs {head}.",
            action=f"Run '{_CLI} db upgrade' (it changes the shared database — run the released version).",
            exit_code=1,
        )


class DatabaseTooNew(CliError):
    """The database was migrated by a newer release than this one: the CLI is the one to update.

    The same `CLI_TOO_OLD` code and exit 6 as `CliTooOld` — the cure is the same.
    """

    def __init__(self, current: str) -> None:
        super().__init__(
            "CLI_TOO_OLD",
            f"The database schema is at revision {current}, which this {_CLI} doesn't know: a newer release migrated it.",
            action=f"Run 'uv tool upgrade {_DIST}', then retry.",
            exit_code=6,
        )


class DataioError(CliError):
    """A failure of reading or writing a table: the address in the message, the next step in the action.

    The one type a tool author catches around `read()` / `write()` / `convert()`;
    the CLI reports it in the standard error envelope like any other CliError.
    """


class SourceNotFound(DataioError):
    """A one-line string is an address (docs/adr/0004): no such source is an error, never silent text."""

    def __init__(self, address: str) -> None:
        super().__init__(
            "SOURCE_NOT_FOUND",
            f"Source '{address}' does not exist.",
            action="Pass format='text' to read the string as text",
            exit_code=2,
        )


class PartNotFound(DataioError):
    """The file has no part (sheet, table) of this name: the action lists the parts it has."""

    def __init__(self, address: str, part: str, parts: list[str]) -> None:
        super().__init__(
            "SOURCE_NOT_FOUND",
            f"Source '{address}' has no part '{part}'." if part else f"Source '{address}' has several parts: name one.",
            action=f"Name one of the parts: {', '.join(parts)}." if parts else "The file has no parts yet.",
            exit_code=2,
        )


class LibraryAction(DataioError):
    """An error whose `action` names a library argument; the CLI shows `cli_action`, which names the flag."""

    def __init__(self, code: str, message: str, *, action: str, cli_action: str, exit_code: int) -> None:
        super().__init__(code, message, action=action, exit_code=exit_code)
        self.cli_action = cli_action

    def for_cli(self) -> LibraryAction:
        """This error with the action worded for the CLI."""
        self.action = self.cli_action
        return self


class SchemaMismatch(LibraryAction):
    """Sources merged with `strict=True` whose columns differ: the message lists the columns of each source."""

    def __init__(self, columns_by_source: dict[str, list[str]]) -> None:
        listed = "; ".join(f"{uri} ({', '.join(columns)})" for uri, columns in columns_by_source.items())
        super().__init__(
            "SCHEMA_MISMATCH",
            f"The sources have different columns: {listed}.",
            action="Pass strict=False to merge them as a union, or fix the columns of the sources.",
            cli_action="Drop --strict to merge them as a union, or fix the columns of the sources.",
            exit_code=2,
        )


class FormatUnknown(DataioError):
    def __init__(self, address: str, known: list[str]) -> None:
        super().__init__(
            "FORMAT_UNKNOWN",
            f"The format of '{address}' is unknown.",
            action=f"Use an extension of a known format or pass format= with one of: {', '.join(known)}.",
            exit_code=2,
        )


class FormatUnsupported(DataioError):
    def __init__(self, message: str, *, action: str) -> None:
        super().__init__("FORMAT_UNSUPPORTED", message, action=action, exit_code=2)


class TargetExists(LibraryAction):
    def __init__(self, address: str) -> None:
        super().__init__(
            "TARGET_EXISTS",
            f"Target '{address}' already exists and the mode is 'error'.",
            action="Pass mode='replace' to replace it, or name another target.",
            cli_action="Pass --mode replace to replace it, or name another target.",
            exit_code=1,
        )


class ConfirmationRequired(DataioError):
    """A replace allowed only on request, as an error there costs most (docs/adr/0005).

    The library asks for `overwrite=True`; the CLI asks `question` first (`--confirm` skips it).
    """

    def __init__(self, message: str, *, question: str, what: str) -> None:
        super().__init__(
            "TARGET_EXISTS",
            message,
            action=f"Pass overwrite=True / --confirm to {what}; a backup is kept.",
            exit_code=1,
        )
        self.question = question


class WriteOverSource(ConfirmationRequired):
    """The target is the source itself."""

    def __init__(self, address: str) -> None:
        super().__init__(
            f"Target '{address}' is the source itself: the write would replace the data it reads.",
            question=f"Write over the source '{address}'",
            what="write over the source",
        )


class NonEmptyPartReplace(ConfirmationRequired):
    """A replace of a part with rows, in a container whose format asks first (a sheet of a Google spreadsheet)."""

    def __init__(self, address: str, rows: int) -> None:
        super().__init__(
            f"Target '{address}' has {rows} rows: a replace of them needs confirmation.",
            question=f"Replace the {rows} rows of '{address}'",
            what="replace it",
        )


class BackupNotFound(DataioError):
    """No kept backup has this id, or none is kept: the action lists the ids there are."""

    def __init__(self, backup_id: str | None, kept: list[str]) -> None:
        super().__init__(
            "SOURCE_NOT_FOUND",
            f"Backup '{backup_id}' does not exist." if backup_id else "No backups are kept.",
            action=f"Pass one of the kept backup ids: {', '.join(kept)}."
            if kept
            else "A replace of an existing target keeps a backup; there is none yet.",
            exit_code=2,
        )


class SheetNotShared(DataioError):
    """A Google spreadsheet not shared with the service account (a 403): the action names whom to share it with."""

    def __init__(self, address: str, email: str) -> None:
        super().__init__(
            "AUTH_REQUIRED",
            f"The service account {email} may not open or change '{address}'.",
            action=f"Share the sheet with {email} as Editor.",
            exit_code=3,
        )


class ReadFailed(DataioError):
    """`action`: what to do instead, when the cause is known (an SQL error); else the check of the file."""

    def __init__(self, address: str, cause: Exception, *, action: str | None = None) -> None:
        super().__init__(
            "READ_FAILED",
            f"Could not read '{address}': {cause}",
            action=action
            or "Check that the source is a valid file of its format; pass encoding= or sep= if they differ.",
            exit_code=1,
        )


class WriteFailed(DataioError):
    """`action`: what to do instead, when the format said so; else the check of the folder."""

    def __init__(self, address: str, cause: Exception, *, action: str | None = None) -> None:
        super().__init__(
            "WRITE_FAILED",
            f"Could not write '{address}': {cause}",
            action=action or "Check that the folder of the target exists and is writable.",
            exit_code=1,
        )


class InvalidParameter(DataioError, InvalidArguments):
    """A library parameter with a value it cannot take: `INVALID_ARGUMENTS`, caught as a DataioError too."""
