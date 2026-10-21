# dataio

Универсальное чтение и запись таблиц: строки, списки, DataFrame, txt, csv, tsv, xlsx, json, jsonl, parquet, Google Sheets, stdin

## Development

```bash
uv sync
uv run dataio --help
uvx --from "git+https://homeserver.tailee01ab.ts.net:3000/bolandeu/cli-generator.git@v1.25.0#subdirectory=gate" rb-release check   # the full gate (run before every commit; CI runs it too)
uv run pytest --snapshot-update  # after changing a command's help; review tests/snapshots/help/
```

`pytest` fails below the coverage floor in `pyproject.toml`; `ruff` includes
the security (`S`) rules; the gate also scans `uv.lock` for known
vulnerabilities when `osv-scanner` is installed (`brew install osv-scanner`),
and says it skipped the scan otherwise. CI repeats
the same gate, `uvx ... rb-release check` (the command above).

## Release

The version is the git tag (`vX.Y.Z`) — `pyproject.toml` has no `version =`.
Work goes through Antagor tickets (`.agents/antagor/`); a release (run by the Human) is

```bash
antagor publish --bump   # SemVer; at 0.x: patch = fix/feature, minor = breaking
```

It tags the release, builds `CHANGELOG.md` from the ticket titles and runs
`scripts/deploy.sh`: push `main` with tags, then report the release to the
root tools agent. Nobody tags or pushes by hand.

## Target columns

Keep some columns, in an order, under new names; every target takes them
(files, stdout, Google Sheets, records in memory). The selection comes first,
then the rename. A wrong name or a clash is refused with exit 2
(`INVALID_ARGUMENTS`); `split_by` and `append` work with them.

```python
write(df, "out.json", columns=["phrase", "similarity"], rename={"similarity": "score"})
```

```bash
dataio convert semkit-out.csv clusters.json --columns phrase,similarity --rename similarity=score
```

## Install

**On this machine, from a local checkout:**

```bash
uv tool install .
```

**On any other machine (any OS), once this repo is pushed to GitHub — no
PyPI publish needed:**

```bash
uv tool install "rb-dataio @ git+https://github.com/bolandeu/rb-dataio.git@vX.Y.Z"
```

Replace `vX.Y.Z` with the latest release tag (a tag cut by
`antagor publish`; never install a branch). This is also how an AI agent
bootstraps this CLI on a fresh machine/sandbox where it isn't installed
yet — see `src/rb_dataio/data/SKILL.md`.

**Private repo?** The command above is unchanged — `uv` runs git under the
hood, so it authenticates the same way `git clone` does. On a machine
where the install is refused with an auth error, do one of these once:

```bash
gh auth login          # interactive login also sets up git's credential helper
gh auth setup-git      # only needed if gh was logged in with --with-token / in CI
```

or use the SSH form instead of HTTPS:

```bash
uv tool install "rb-dataio @ git+ssh://git@github.com/bolandeu/rb-dataio.git@vX.Y.Z"
```

**Update** an installed copy to the latest commit:

```bash
uv tool upgrade rb-dataio
```

After install, the command `dataio` is available globally, on
macOS, Linux and Windows alike (see `architecture.md` in the cli-generator
plugin for why: no shelling out, no hardcoded POSIX paths).

To pick up later architecture changes from the `cli-generator` template
itself, run `copier update` in this repo (requires this repo and the
template to both be git repos; see the `cli-generator` plugin's README).

## Architecture

This project follows a fixed CLI architecture:

- `src/rb_dataio/commands/` — argument parsing only, no business logic.
- `src/rb_dataio/core/` — services, models, errors: the real logic.
- `src/rb_dataio/providers/` — external APIs/integrations.
- `src/rb_dataio/credentials/` — secrets via the OS keychain (`keyring`)
  and environment variables. Secrets never live in `.rb_dataio/config.toml`.
- `src/rb_dataio/output/` — human (`rich`) and `--json` rendering.

Run `dataio doctor` to check environment/config/auth readiness, and
`dataio --help` for the full command surface. Every command supports
`--json` for machine/agent consumption; errors are structured (`error.code`,
fixed exit codes, `error.action` telling you what to do next) and go to
stderr in human mode, so stdout is always safe to pipe.

A project can require a minimum CLI version in its `.rb_dataio/config.toml`
(`[cli] min_version = "..."`); an older install refuses with exit 6 and
`uv tool upgrade rb-dataio` fixes it.

See `src/rb_dataio/data/SKILL.md` for the agent-facing usage guide
bundled with this package — install it into an AI tool with
`dataio skill install`, or get it as plain text with
`dataio --ai` (works even without file access).
