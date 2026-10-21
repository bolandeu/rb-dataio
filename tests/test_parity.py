"""The library and the CLI have the same parameters (docs/adr/0001).

`read()` and `write()` reach the CLI through `convert`: the options both sides have
take `in_` / `out_` there, the others keep their names. Every keyword of `convert()`,
`info()` and `join()` is a flag of the command with the same name: `_` becomes `-`, a boolean
is `--x/--no-x`, a dict or a list is a repeatable flag; the default is the same. `lookups` is the flag `--lookup`.
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

from rb_dataio import convert, info, join, output, read, write
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


FLAG_NAMES = {"lookups": "--lookup"}  # a repeatable flag is named in the singular


@pytest.mark.parametrize(("function", "command"), [(convert, "convert"), (info, "info"), (join, "join")])
def test_every_keyword_is_a_flag_with_the_same_name(function: Callable, command: str) -> None:
    keywords = _keywords(function)
    flags = _flag_params(command)
    assert set(flags) == set(keywords), f"`{command}` flags differ from the keywords of its library function"
    hints = typing.get_type_hints(function)
    for name, param in keywords.items():
        flag = flags[name]
        dashed = FLAG_NAMES.get(name, "--" + name.replace("_", "-"))
        assert dashed in flag.opts, f"`{command}` has no {dashed}"
        if flag.default is not None or param.default is not None:
            assert flag.default == param.default, f"{dashed}: default {flag.default!r} != {param.default!r}"
        hint = hints[name]
        if hint is bool and name != "dry_run":
            assert flag.secondary_opts == [f"--no-{dashed[2:]}"], f"{dashed} needs --no-{dashed[2:]}"
        if dict in {typing.get_origin(arg) for arg in typing.get_args(hint)}:
            assert flag.multiple, f"{dashed} must be repeatable (key=value)"
        if typing.get_origin(hint) is list or list in {typing.get_origin(arg) for arg in typing.get_args(hint)}:
            assert flag.multiple, f"{dashed} must be repeatable"


def test_join_takes_the_convert_keywords_of_its_sources_and_target() -> None:
    joined = set(_keywords(join)) - {"lookups", "on", "how"}
    assert joined <= set(_keywords(convert))
    assert joined == {name for name in _keywords(convert) if name.startswith(("in_", "out_"))} | {
        "mode",
        "start",
        "value_input",
        "columns",
        "rename",
        "overwrite",
        "backup",
        "dry_run",
    }


@pytest.mark.parametrize("command", ["convert", "info"])
def test_query_is_a_source_option_without_a_prefix(command: str) -> None:
    assert "query" in _keywords(read)
    assert "--query" in _flag_params(command)["query"].opts
    assert "in_query" not in _flag_params(command)


def test_start_and_value_input_are_target_options_without_a_prefix() -> None:
    assert {"start", "value_input"} <= _keywords(write).keys() - _keywords(read).keys()
    flags = _flag_params("convert")
    assert (flags["start"].opts[0], flags["value_input"].opts[0]) == ("--start", "--value-input")
    assert _keywords(write)["value_input"].default == flags["value_input"].default == "raw"


def test_credentials_is_an_option_of_both_sides() -> None:
    assert "credentials" in _keywords(read).keys() & _keywords(write).keys()
    flags = _flag_params("convert")
    assert {"--in-credentials", "--out-credentials"} == {*flags["in_credentials"].opts, *flags["out_credentials"].opts}
