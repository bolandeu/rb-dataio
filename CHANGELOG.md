# Changelog

All notable changes to this project are documented here. Versions follow
[SemVer](https://semver.org/) (while at `0.x`, a minor bump may break).

The changelog is written by `antagor publish`; don't edit it by hand.

## v0.1.4 — 2026-10-16

### E-001 — dataio core: the connector and its contract (0.2)

The library has read/write/convert/info/formats/backups/restore and the CLI has the same capabilities (convert, info, formats, backups, restore). Python objects, txt, csv, tsv, json, jsonl and stdin/stdout work; encoding and delimiter are detected and shown in the report; every error has a code and an action; every replace keeps a backup that restore brings back.
Time: 1.7h since the epic was approved

- Backup safety fixes: content file name, no hard links, size check before parsing (DATAIO-005)

## v0.1.3 — 2026-10-16

### E-001 — dataio core: the connector and its contract (0.2)

The library has read/write/convert/info/formats/backups/restore and the CLI has the same capabilities (convert, info, formats, backups, restore). Python objects, txt, csv, tsv, json, jsonl and stdin/stdout work; encoding and delimiter are detected and shown in the report; every error has a code and an action; every replace keeps a backup that restore brings back.
Time: 1.6h since the epic was approved

- Formats and values: CSV/TSV/txt with detection and normalisation, Python objects, JSON/jsonl and stdin/stdout (DATAIO-002)

## v0.1.2 — 2026-10-16

### E-001 — dataio core: the connector and its contract (0.2)

The library has read/write/convert/info/formats/backups/restore and the CLI has the same capabilities (convert, info, formats, backups, restore). Python objects, txt, csv, tsv, json, jsonl and stdin/stdout work; encoding and delimiter are detected and shown in the report; every error has a code and an action; every replace keeps a backup that restore brings back.
Time: 1.3h since the epic was approved

- Protection: backups, restore, atomic writes, write modes, safety checks and loss warnings (DATAIO-004)

## v0.1.1 — 2026-10-16

### E-001 — dataio core: the connector and its contract (0.2)

The library has read/write/convert/info/formats/backups/restore and the CLI has the same capabilities (convert, info, formats, backups, restore). Python objects, txt, csv, tsv, json, jsonl and stdin/stdout work; encoding and delimiter are detected and shown in the report; every error has a code and an action; every replace keeps a backup that restore brings back.
Time: 1h since the epic was approved

- Core frame: read/write/convert/info/formats through the address, the format registry and the report, with the full CLI surface (DATAIO-001)
