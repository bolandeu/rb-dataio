"""The library and the CLI have the same parameters (docs/adr/0001).

`read()` and `write()` reach the CLI through `convert`: the options both sides have
take `in_` / `out_` there, the others keep their names. Every keyword of `convert()`
and `info()` is a flag of the command with the same name: `_` becomes `-`, a boolean
is `--x/--no-x`, a dict is a repeatable `key=value` flag; the default is the same.
The template's standard flags (`--json`, `--quiet`, `--dry-run`, ...) keep the
template's own shape. A missing or an extra flag fails.
"""

from __future__ import annotations

import inspect
import typing
from collections.abc import Callable
from typing import Any

import pytest
import typer

from rb_dataio import convert, info, output, read, write
from rb_dataio.cli import app

# Recent Typer ships its own copy of Click: parameters are told apart by `param_type_name`, not isinstance.
COMMANDS: dict[str, Any] = typer.main.get_command(app).commands  # ty: ignore[unresolved-attribute]
TEMPLATE_FLAGS = {
    output.JsonOption,
    output.QuietOption,
    output.VerboseOption,
    output.DryRunOption,
    output.ConfirmOption,
    output.NonInteractiveOption,
}


def _keywords(function: Callable) -> dict[str, inspect.Parameter]:
    return {
        name: param
        for name, param in inspect.signature(function).parameters.items()
        if param.kind is inspect.Parameter.KEYWORD_ONLY
    }


def _flag_params(name: str) -> dict[str, Any]:
    """The command's options by their Python name, without the template's output flags (kept apart by identity)."""
    callback = inspect.unwrap(COMMANDS[name].callback)
    template = {
        param_name
        for param_name, param in inspect.signature(callback).parameters.items()
        if param.default in TEMPLATE_FLAGS and param_name != "dry_run"
    }
    return {
        param.name: param
        for param in COMMANDS[name].params
        if param.param_type_name == "option" and param.name not in template
    }


def test_convert_takes_every_read_and_write_keyword() -> None:
    read_side, write_side = _keywords(read), _keywords(write)
    both = read_side.keys() & write_side.keys()
    expected = {
        *(f"in_{name}" for name in both),
        *(f"out_{name}" for name in both),
        *(read_side.keys() - both),
        *(write_side.keys() - both),
    }
    assert set(_keywords(convert)) == expected


def test_info_takes_the_read_keywords() -> None:
    assert {name: p.default for name, p in _keywords(info).items()} == {
        name: p.default for name, p in _keywords(read).items()
    }


@pytest.mark.parametrize(("function", "command"), [(convert, "convert"), (info, "info")])
def test_every_keyword_is_a_flag_with_the_same_name(function: Callable, command: str) -> None:
    keywords = _keywords(function)
    flags = _flag_params(command)
    assert set(flags) == set(keywords), f"`{command}` flags differ from the keywords of its library function"
    hints = typing.get_type_hints(function)
    for name, param in keywords.items():
        flag = flags[name]
        dashed = "--" + name.replace("_", "-")
        assert dashed in flag.opts, f"`{command}` has no {dashed}"
        if flag.default is not None or param.default is not None:
            assert flag.default == param.default, f"{dashed}: default {flag.default!r} != {param.default!r}"
        hint = hints[name]
        if hint is bool and name != "dry_run":
            assert flag.secondary_opts == [f"--no-{dashed[2:]}"], f"{dashed} needs --no-{dashed[2:]}"
        if dict in {typing.get_origin(arg) for arg in typing.get_args(hint)}:
            assert flag.multiple, f"{dashed} must be repeatable (key=value)"
