# CodeSaver CLI source

This directory contains the CodeSaver CLI implementation (v1.4.1).

- `cli.py` — command-line argument handling and interactive commands.
- `core.py` — backup, restore, filtering, retention, and archive logic.
- `config.py` — project configuration loading.
- `lang.py` — localized CLI messages and system-locale detection.
- `logging_utils.py` — optional operation logging.

The CLI is tested with Python 3.9+ and is distributed for Windows, macOS, and
Linux in the [latest CLI release](https://github.com/vibecraft01/CodeSaver/releases).
