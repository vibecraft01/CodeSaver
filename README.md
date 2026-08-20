# CodeSaver

[![CI](https://github.com/vibecraft01/CodeSaver/actions/workflows/ci.yml/badge.svg)](https://github.com/vibecraft01/CodeSaver/actions/workflows/ci.yml)

CodeSaver is a cross-platform code backup utility for developers. It creates timestamped ZIP snapshots, restores projects safely, supports unattended autosave, and provides both a scriptable CLI and an optional PyQt5 Desktop application.

## Current versions

| Component | Version | Runtime | Distribution |
| --- | --- | --- | --- |
| CodeSaver CLI | **1.1.4** | Python 3.9+ | [CLI release](https://github.com/vibecraft01/CodeSaver/releases/tag/v1.1.4) |
| CodeSaver Desktop | **1.0.1** | Python 3.10+ with PyQt5 | [Desktop release](https://github.com/vibecraft01/CodeSaver/releases/tag/desktop-v1.0.1) |

The CLI and Desktop applications share the same tested backup and restore engine. Installing the CLI does not install PyQt5.

## Features

### CLI

- Timestamped ZIP archives using `YYYY-MM-DD_HH-MM-SS`.
- Background autosave every 10 minutes by default.
- Interactive backup and restore menu.
- Automatic locale detection with 12 supported languages.
- Localized help, prompts, progress messages, and errors.
- Default exclusions for `.git`, `__pycache__`, virtual environments, build directories, and caches.
- Zip Slip protection during restore.
- File and byte progress reporting.
- Estimated time remaining (ETA) in progress output.
- Maximum compression with `--compress`.
- File-size filtering with `--max-size`.
- Automatic cleanup with `--keep-last N`.
- Age-based cleanup with `--keep-days N`.
- Root `.gitignore` support with common glob and negation rules.
- Repeatable extension filtering with `--exclude-ext`.
- JSON glob templates such as `*.tmp`, `*.log`, and `temp_*`.
- Optional symbolic-link traversal with `--follow-symlinks`.
- Recent-project selection when starting `codesaver` without arguments.
- Unreadable files are reported with their path and skipped so the backup can continue.
- Optional operation logs with `--log`.
- JSON configuration through `.codesaver.json` or `--config`.
- Python 3.9+ dependency-free runtime.

### Desktop version

CodeSaver Desktop `1.0.1` is a graphical alternative for developers who prefer a visual workflow. It includes:

- Project folder selection with file count and total size.
- Create and restore backup buttons.
- Backup table with archive name, creation date, and size.
- Double-click restore from the archive list.
- Real-time progress for files and processed bytes.
- Settings for excluded directories, excluded extensions, compression, autosave, retention, language, theme, backup location, and tray behavior.
- Dark GitHub-style theme and light theme.
- Optional system-tray mode and desktop notifications.
- No API keys or external services.

## Desktop interface preview

The main window is organized as a compact developer dashboard:

```text
+-----------------------------------------------------------------------+
| CodeSaver Desktop                         [Open folder] [Settings]    |
| Project: C:\Projects\demo   Files: 42   Size: 8.6 MB                 |
+-----------------------------------------------------------------------+
| [Create backup] [Restore backup]                                      |
|                                                                       |
| Archive name                         Created              Size        |
| demo_2026-08-20_12-30-00.zip        2026-08-20 12:30     2.1 MB      |
|                                                                       |
| Progress: 42/42 files - 8.6 MB/8.6 MB                         100%    |
| Ready                                                                 |
+-----------------------------------------------------------------------+
```

The Settings dialog centralizes project exclusions, autosave, retention, language, theme, compression, and storage preferences.

## Supported languages

The CLI detects `LC_ALL`, `LC_MESSAGES`, `LANG`, `LANGUAGE`, and the system locale. Use `--language` to override detection for one run.

| Language | Documentation |
| --- | --- |
| English | [README.en.md](docs/README.en.md) |
| Russian | [README.ru.md](docs/README.ru.md) |
| Ukrainian | [README.uk.md](docs/README.uk.md) |
| German | [README.de.md](docs/README.de.md) |
| French | [README.fr.md](docs/README.fr.md) |
| Spanish | [README.es.md](docs/README.es.md) |
| Portuguese | [README.pt.md](docs/README.pt.md) |
| Chinese | [README.zh.md](docs/README.zh.md) |
| Japanese | [README.ja.md](docs/README.ja.md) |
| Korean | [README.ko.md](docs/README.ko.md) |
| Hindi | [README.hi.md](docs/README.hi.md) |
| Arabic | [README.ar.md](docs/README.ar.md) |

```bash
codesaver --language de
codesaver --language zh --backup-now
```

## Installation

Python 3.9 or newer is required for the CLI.

```bash
git clone https://github.com/vibecraft01/CodeSaver.git
cd CodeSaver
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -e .
```

## CLI usage

Start the interactive menu:

```bash
codesaver
```

Create one backup and exit:

```bash
codesaver --project-dir ./my-project --backup-dir ./backups --backup-now
```

Useful backup controls:

```bash
# Maximum DEFLATE compression; exclude files larger than 100 MB.
codesaver --backup-now --compress --max-size 100M

# Keep only the five newest backups.
codesaver --backup-now --keep-last 5

# Delete backups older than 30 days.
codesaver --backup-now --keep-days 30

# Include the contents reached through symbolic links.
codesaver --backup-now --follow-symlinks

# Exclude temporary and log files by extension.
codesaver --backup-now --exclude-ext .tmp --exclude-ext .log

# Ignore the project's .gitignore for this run.
codesaver --backup-now --no-gitignore
```

Example progress output:

```text
Progress: 12/48 files (25%) - 1.4 MB/5.8 MB; ETA: 18s
Progress: 48/48 files (100%) - 5.8 MB/5.8 MB; ETA: 0s
Backup created: /path/to/my-project-backups/my-project_2026-08-20_12-30-00.zip
```

Restore an archive:

```bash
codesaver --project-dir ./my-project \
  --restore ./backups/my-project_2026-01-20_14-30-00.zip \
  --overwrite
```

Disable autosave with `--no-autosave` or change the interval with `--interval 300` seconds.

## Configuration

CodeSaver looks for `.codesaver.json` in the project directory. A ready-to-copy example is included in this repository:

```json
{
  "interval": 600,
  "language": "en",
  "backup_dir": "../code-saver-backups",
  "log": "../code-saver.log",
  "excluded_dirs": [".git", "__pycache__", "venv", ".venv", "build"],
  "exclude_ext": [".tmp", ".log", ".pyc"],
  "exclude_patterns": ["*.tmp", "*.log", "temp_*"],
  "compress": true,
  "max_size": "100M",
  "keep_last": 5,
  "keep_days": 30,
  "follow_symlinks": false,
  "use_gitignore": true
}
```

Paths are resolved relative to the configuration file. Command-line values override configuration values.

## Install and build Desktop

### Install from source

```bash
python -m pip install -e ".[desktop]"
python -m desktop.main
```

The installed entry point is also available:

```bash
codesaver-desktop
```

### Download a standalone package

The current stable binary is available in the [Desktop v1.0.1 release](https://github.com/vibecraft01/CodeSaver/releases/tag/desktop-v1.0.1):

- `CodeSaverDesktop-windows-x64.exe` for Windows.
- `CodeSaverDesktop-macos.zip` containing the macOS application.
- `CodeSaverDesktop-linux-amd64.deb` for Debian-based Linux distributions.

The stable [CLI v1.1.4 release](https://github.com/vibecraft01/CodeSaver/releases/tag/v1.1.4) is also available.

### Build from source

The repository includes platform scripts and a reviewed `CodeSaverDesktop.spec` PyInstaller definition:

```powershell
# Windows PowerShell
.\scripts\build_desktop.ps1
```

```bash
# macOS: creates dist/CodeSaverDesktop.app and a ZIP archive.
sh scripts/build_desktop_macos.sh

# Linux: creates a one-file binary and a .deb when dpkg-deb is available.
sh scripts/build_desktop_linux.sh
```

To invoke PyInstaller directly:

```bash
python -m pip install -e ".[desktop,release]"
python -m PyInstaller --clean --noconfirm CodeSaverDesktop.spec
```

## Logging and error handling

Save timestamped operation logs to a file:

```bash
codesaver --project-dir ./my-project --backup-now --log ./logs/codesaver.log
```

The CLI returns a non-zero exit code and a localized message for missing paths, permission errors, invalid configuration, damaged ZIP files, and invalid autosave intervals. Restore refuses unsafe archive paths and does not replace existing files unless `--overwrite` is provided.

## Development

Run the test suite:

```bash
python -m unittest discover -s tests -v
```

Optional formatting and linting checks:

```bash
python -m pip install -e ".[dev]"
python -m black --check codesaver desktop tests scripts
python -m flake8 codesaver desktop tests scripts
```

See [CONTRIBUTING.md](CONTRIBUTING.md), [CHANGELOG.md](CHANGELOG.md), and [LICENSE](LICENSE).

## License

MIT. See [LICENSE](LICENSE).
