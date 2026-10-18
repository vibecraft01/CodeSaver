# CodeSaver CLI source

This directory contains the CodeSaver CLI implementation (v1.9.0).

- `cli.py` — command-line argument handling and interactive commands.
- `core.py` — backup, restore, filtering, retention, and archive logic.
- `backup_metadata.py` — persistent local archive labels, notes, search, and catalog export.
- `evolution.py` — file-level comparisons between consecutive backup snapshots and CSV export.
- `config.py` — project configuration loading.
- `lang.py` — localized CLI messages and system-locale detection.
- `logging_utils.py` — optional operation logging.

The CLI is tested with Python 3.9+ and is distributed for Windows, macOS, and
Linux in the [latest CLI release](https://github.com/vibecraft01/CodeSaver/releases).

CLI 1.9.0 adds backup-evolution reports, path filtering, CSV export, and an
optional nonzero exit for detected changes. See the [release notes](../docs/releases/v1.9.0.md).
