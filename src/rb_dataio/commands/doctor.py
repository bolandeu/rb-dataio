"""The `doctor` command: diagnostic checks and the `healthy` verdict.

A missing project and a missing OS keychain are reported, not failed: dataio
works without them. The credential check follows the `auth status` rule.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import typer

from .. import output
from ..core import deps, services
from ..core.errors import CliTooOld
from ..core.models import ProjectConfig
from ..core.version import DEV_VERSION, cli_name, installed_version, module_exists

_PACKAGE_NAME = __name__.split(".")[0]


def _auth_checks() -> list[dict]:
    # credentials/ is dropped at generation time when include_auth=false;
    # detecting it at runtime keeps this file free of template logic.
    if not module_exists(f"{_PACKAGE_NAME}.credentials.manager"):
        return []
    credentials = importlib.import_module(f"{_PACKAGE_NAME}.credentials.manager")
    health = importlib.import_module(f"{_PACKAGE_NAME}.credentials.health")

    backend = credentials.store_backend()
    return [
        {
            "name": "credential_store",
            "ok": True,
            "detail": backend or "no OS keychain; credentials come from environment variables",
        },
        health.doctor_check(cli_name(), installed_version() or DEV_VERSION),
    ]


@output.guard
def doctor(
    ctx: typer.Context,
    json_output: bool = output.JsonOption,
    quiet: bool = output.QuietOption,
    verbose: bool = output.VerboseOption,
) -> None:
    """Run diagnostic checks and report readiness.

    Always exits 0 — the report itself is the result; `healthy` says
    whether every check passed.

    Example: {cli} doctor --json
    """
    checks: list[dict] = [{"name": "python", "ok": True}]
    checks.append({"name": "cli_version", "ok": True, "detail": installed_version() or DEV_VERSION})

    start = Path(ctx.obj.get("project") or Path.cwd())
    output.vecho(ctx, f"Searching for a project root starting at: {start}")
    root = services.find_project_root(start)
    checks.append({"name": "project", "ok": True, "detail": str(root) if root else "no project; dataio works without one"})

    config: ProjectConfig | None = None
    if root is not None:
        try:
            config = services.load_config(root, check_compat=False)
            checks.append({"name": "config", "ok": True})
        except Exception as exc:
            checks.append({"name": "config", "ok": False, "detail": str(exc)})
    if config is not None:
        try:
            services.check_cli_compat(config)
            checks.append({"name": "cli_compat", "ok": True, "detail": f"project requires >= {config.cli.min_version}"})
        except CliTooOld as exc:
            checks.append({"name": "cli_compat", "ok": False, "detail": exc.message})

    checks.extend(_auth_checks())
    checks.extend(deps.doctor_checks())  # [[tool.rb.external]] in pyproject.toml
    if module_exists(f"{_PACKAGE_NAME}.core.db"):  # include_db=false drops it at generation time
        checks.extend(importlib.import_module(f"{_PACKAGE_NAME}.core.db").doctor_checks())

    all_ok = all(check["ok"] for check in checks)
    output.emit_success(
        ctx, {"healthy": all_ok, "checks": checks}, render_human=lambda data: output.human.render_doctor(data["checks"])
    )
