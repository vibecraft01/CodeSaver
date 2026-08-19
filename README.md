# CodeSaver

[![CI](https://github.com/vibecraft01/CodeSaver/actions/workflows/ci.yml/badge.svg)](https://github.com/vibecraft01/CodeSaver/actions/workflows/ci.yml)

CodeSaver is a lightweight, cross-platform CLI utility that creates reliable ZIP snapshots of source-code projects. It uses only Python's standard library and automatically speaks the language configured by the operating system.

## Features

- Timestamped ZIP archives using `YYYY-MM-DD_HH-MM-SS`.
- Background autosave every 10 minutes by default.
- Interactive console menu for backup and restore.
- Automatic locale detection with 12 supported languages.
- Localized help, prompts, progress messages, and errors.
- Excludes `.git`, `__pycache__`, `venv`, `.venv`, `env`, `.tox`, and `.mypy_cache` by default.
- Zip Slip protection during restore.
- Progress reporting while files are added to an archive.
- Optional maximum ZIP compression with `--compress`.
- File-size filtering with `--max-size` (supports bytes, `K/M/G`, and `KiB/MiB/GiB`).
- Real-time progress with processed and total data size.
- Automatic cleanup with `--keep-last N`.
- Automatic root `.gitignore` support, including common glob and negation rules.
- Optional operation logs written with `--log`.
- JSON configuration through `.codesaver.json` or `--config`.
- No runtime dependencies outside Python 3.9+.

## Supported languages

| Language | Documentation |
| --- | --- |
| English | [README.en.md](docs/README.en.md) |
| Русский | [README.ru.md](docs/README.ru.md) |
| Українська | [README.uk.md](docs/README.uk.md) |
| Deutsch | [README.de.md](docs/README.de.md) |
| Français | [README.fr.md](docs/README.fr.md) |
| Español | [README.es.md](docs/README.es.md) |
| Português | [README.pt.md](docs/README.pt.md) |
| 中文 | [README.zh.md](docs/README.zh.md) |
| 日本語 | [README.ja.md](docs/README.ja.md) |
| 한국어 | [README.ko.md](docs/README.ko.md) |
| हिन्दी | [README.hi.md](docs/README.hi.md) |
| العربية | [README.ar.md](docs/README.ar.md) |

CodeSaver detects `LC_ALL`, `LC_MESSAGES`, `LANG`, `LANGUAGE`, and the system locale. Use `--language` to override detection for a single run:

```bash
codesaver --language de
codesaver --language zh --backup-now
```

## Installation

Python 3.9 or newer is required.

```bash
git clone https://github.com/vibecraft01/CodeSaver.git
cd CodeSaver
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -e .
```

## Usage

Start the interactive menu in the current project:

```bash
codesaver
```

Create one backup and exit:

```bash
codesaver --project-dir ./my-project --backup-dir ./backups --backup-now
```

During a backup CodeSaver reports files and data processed in real time:

```text
Progress: 12/48 files (25%) — 1.4 MB/5.8 MB
Progress: 48/48 files (100%) — 5.8 MB/5.8 MB
Backup created: /path/to/my-project-backups/my-project_2026-08-19_16-30-00.zip
```

Useful backup controls:

```bash
# Maximum DEFLATE compression; exclude files larger than 100 MB.
codesaver --backup-now --compress --max-size 100M

# Keep only the five newest backups for this project.
codesaver --backup-now --keep-last 5

# Ignore the project's .gitignore for this run.
codesaver --backup-now --no-gitignore
```

The root `.gitignore` is applied automatically. Files larger than `--max-size` are not counted in the archive or progress totals. Size values may be plain bytes (`104857600`), decimal units (`100M`), or binary units (`100MiB`).

Restore an archive:

```bash
codesaver --project-dir ./my-project \
  --restore ./backups/my-project_2026-01-20_14-30-00.zip \
  --overwrite
```

Disable autosave with `--no-autosave`. Change the interval with `--interval 300` (seconds). Stop the interactive application with `Ctrl+C`.

## Configuration

CodeSaver looks for `.codesaver.json` in the project directory. A ready-to-copy example is included in this repository:

```json
{
  "interval": 600,
  "language": "en",
  "backup_dir": "../code-saver-backups",
  "log": "../code-saver.log",
  "excluded_dirs": [".git", "__pycache__", "venv", ".venv", "build"],
  "compress": true,
  "max_size": "100M",
  "keep_last": 5,
  "use_gitignore": true
}
```

Paths in the configuration are resolved relative to the configuration file, so the same file works on Windows, Linux, and macOS. Use another file explicitly with `--config ./settings.json`; command-line values override configuration values.

## Logging and error handling

Save timestamped operation logs to a file:

```bash
codesaver --project-dir ./my-project --backup-now --log ./logs/codesaver.log
```

The CLI returns a non-zero exit code and a localized message for missing paths, permission errors, invalid configuration, damaged ZIP files, and invalid autosave intervals. Restore is protected against path traversal and refuses to replace existing files unless `--overwrite` is provided.

## Release files for Windows, macOS, and Linux

GitHub Releases contain standalone artifacts built by GitHub Actions:

- `CodeSaver-windows-x64.exe` for Windows.
- `CodeSaver-macos-x64` for macOS Terminal.
- `CodeSaver-linux-x64` for Linux.

The Python installation remains available on every platform. For macOS/Linux, use `scripts/install.sh`; for Windows PowerShell, use `scripts/install.ps1`:

```bash
sh scripts/install.sh
```

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install.ps1
```

The standalone files are console applications, so they preserve CodeSaver's interactive menu and progress output.

## Cross-platform notes

CodeSaver uses `pathlib.Path` and `os.path` for filesystem operations and has no OS-specific shell commands. The same commands work in PowerShell, Command Prompt, Bash, and Zsh. On Windows, the CLI configures UTF-8 output so translated help and status messages remain readable.

## Development

Run the test suite without installing pytest:

```bash
python -m unittest discover -s tests -v
```

Optional formatting and linting checks:

```bash
python -m pip install -e ".[dev]"
python -m black --check codesaver tests
python -m flake8 codesaver tests
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines and [CHANGELOG.md](CHANGELOG.md) for release history.

## License

MIT. See [LICENSE](LICENSE).
