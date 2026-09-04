# CodeSaver

[![CI](https://github.com/vibecraft01/CodeSaver/actions/workflows/ci.yml/badge.svg)](https://github.com/vibecraft01/CodeSaver/actions/workflows/ci.yml)

CodeSaver is a cross-platform code backup utility for developers. It creates timestamped ZIP snapshots, restores projects safely, supports unattended autosave, and provides both a scriptable CLI and an optional PyQt5 Desktop application.

## Current versions

| Component | Version | Runtime | Distribution |
| --- | --- | --- | --- |
| CodeSaver CLI | [**1.4.3**](https://github.com/vibecraft01/CodeSaver/releases/tag/v1.4.3) | Python 3.9+ | Updated 2026-09-04 |
| CodeSaver Desktop | [**1.3.1**](https://github.com/vibecraft01/CodeSaver/releases/tag/desktop-v1.3.1) | Python 3.10+ with PyQt5 | Updated 2026-09-04 |

The CLI and Desktop applications share the same tested backup and restore engine. Installing the CLI does not install PyQt5.

## Impact snapshot

GitHub repository snapshot for **3 September 2026**:

| Metric | Value |
| --- | ---: |
| Git clones (last 14 days) | 2,517 |
| Unique cloners | 154 |
| Repository views | 997 |
| Unique visitors | 19 |
| GitHub stars | 8 |
| Public releases | 56 |
| Commits | 122 |

These figures are reported as a dated project snapshot; GitHub clones can include automation and are not presented as unique users.

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
- Dry-run file listing with `--dry-run`.
- ZIP integrity validation with `--verify`.
- SHA-256 file manifests with `--manifest` for auditable archive contents.
- Repeatable command-line directory exclusions with `--exclude-dir`.
- Safe archive inspection with `--list ARCHIVE` without restoring files.
- Repeatable command-line glob exclusions with `--exclude-pattern`.
- Quiet automation mode with `--quiet` and machine-readable backup results with `--json`.
- Auditable JSON backup reports with `--report report.json`.
- Archive health checks with `--health` and CI-friendly `--health --json` output.
- Backup inventory reports with `--stats` and `--stats --json`.
- Developer project summary with extension counts via `--project-summary`.
- Searchable backup archive names via `--archive-search`.
- Structured Git working-tree status via `--git-status-json`.
- CSV project inventory export via `--export-inventory`.
- Safe archive restore preview via `--restore-preview`.
- Optional cloud upload via `--cloud-upload ARCHIVE --cloud-url URL`.
- Cloud credentials are read from `CODESAVER_CLOUD_TOKEN` or a custom token variable.
- Desktop duplicate-file detection using SHA-256.
- Desktop archive-integrity report export.
- Desktop backup-storage free-space diagnostics.
- One-click copying of a restore command.
- File-name search inside a selected ZIP archive.
- Compare two ZIP archives with added, removed, and changed file counts.
- Export SHA-256 hashes for every file in an archive as CSV.
- Inspect the total unpacked size of a selected archive.
- Preview retention cleanup before deleting old backups.
- Copy a selected archive manifest as JSON to the clipboard.
- Git-ignored file inspection with `--gitignored-files`.
- Size-aware project tree output with `--project-tree`.
- Text search across readable source files with `--search-content`.
- File extension counts and storage totals with `--extension-report`.
- Per-archive verification results with `--health-report`.
- `--version` for scripts and support diagnostics.
- JSON backup plans with `--plan-json FILE`.
- Exportable archive verification reports with `--verify-report FILE`.
- Git remote inspection with `--git-remote`.
- Starter configuration generation with `--config-template FILE`.
- Project drift auditing with `--diff ARCHIVE`, showing added, modified, and missing files; use `--json` for CI.
- Final verification and operation summary output.
- Optional operation logs with `--log`.х
- JSON configuration through `.codesaver.json` or `--config`.
- Python 3.9+ dependency-free runtime.

### Desktop version

CodeSaver Desktop `1.3.0` is a graphical alternative for developers who prefer a visual workflow. It includes:
- Archive health CSV export, project-directory overview, Git history copying, compression report CSV export, and backup age map.
- Archive extension summary, project-size CSV export, backup-summary JSON copying, duplicate archive-member detection, and restore-preview copying.

- Project folder selection with file count and total size.
- Create and restore backup buttons.
- Backup table with archive name, creation date, and size.
- Double-click restore from the archive list.
- Real-time progress for files and processed bytes.
- Settings for excluded directories, excluded extensions, compression, autosave, retention, language, theme, backup location, and tray behavior.
- System, dark, light, Midnight, Ocean, Forest, and High Contrast themes with a custom accent color.
- Automatic system-language detection, Russian/English switching, and optional backup on startup.
- Optional system-tray mode and desktop notifications.
- Drag-and-drop project folder selection.
- Recent-project menu with the five latest project folders.
- Confirmation dialogs before restore and old-backup cleanup.
- Low-disk-space warning below 1 GB before a backup starts.
- Backup progress percentage displayed in the system-tray icon.
- Clear warnings when individual files cannot be read.
- Real-time archive search and background integrity verification for selected backups.
- Manual and automatic backup-list refresh every 30 seconds.
- Backup storage summary with archive count and total disk usage.
- Archive context menu for copying paths and opening the containing folder.
- Keyboard shortcuts: `Ctrl+B` backup, `Ctrl+R` restore, and `F5` refresh.
- Verify all saved archives in the background with a health summary.
- Live countdown to the next scheduled autosave.
- Compare the current project with any selected backup before restoring.
- View added, modified, and missing files in a restore-safety report.
- Use `Ctrl+D` to compare the selected archive instantly.
- Automatic ZIP integrity verification after each backup (configurable).
- `Ctrl+Shift+V` shortcut to verify the selected backup immediately.
- Archive details view with file count, size, creation date, and full path.
- Plain-text archive manifest export for audits and indexing.
- Safe archive renaming with collision protection.
- Individual archive deletion with explicit confirmation.
- One-click opening of the active project folder from an archive.
- SHA-256 checksum shown with archive details for reproducible artifact checks.
- JSON manifest export for scripts, audits, and backup indexing.
- Sortable archive table and live result count while filtering backups.
- `Ctrl+F` shortcut to focus and select the backup search field.
- Copy the project path and archive SHA-256 directly from the context menu.
- Open a platform terminal in the active project directory.
- `Ctrl+L` clears the archive search field for a clean inventory view.
- Seven keyboard shortcuts cover backup, restore, compare, verify, search, terminal, and archive audit actions.
- Developer dashboard with eight live project and Git health metrics.
- Export and copy the live developer dashboard for issue reports and CI notes.
- Project tools for CSV file inventory, exclusion review, symlink scanning, Git context copying, and configuration access.
- File-type inventory, stale-file detection, total archive storage, Git-tag viewing, and clipboard backup-index export.
- Archive compression-ratio inspection, timeline CSV export, project file-list copying, archive member dates, and project-info JSON copying.
- Recently modified-file view, archive-member CSV export, archive/project size comparison, archive age display, and project inventory JSON copying.
- Open the current Git diff, refresh analysis, and pause/resume autosave from dedicated actions.
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

See the complete [installation guide](docs/INSTALLATION.md) for source setup, release binaries, first backup, and troubleshooting.

### Install the CLI from PyPI

Once published, the CLI can be installed into any Python 3.9+ environment with:

```bash
python -m pip install codesaver
codesaver --self-check
```

For the optional PyQt5 Desktop application:

```bash
python -m pip install "codesaver[desktop]"
codesaver-desktop
```

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

Compare the current project with an existing backup before restoring it:

```bash
codesaver --project-dir ./my-project --diff ./backups/latest.zip
codesaver --project-dir ./my-project --diff ./backups/latest.zip --json
```

Useful backup controls:

```bash
# Maximum DEFLATE compression; exclude files larger than 100 MB.
codesaver --backup-now --compress --max-size 100M

# Keep only the five newest backups.
codesaver --backup-now --keep-last 5
codesaver --backup-now --manifest --verify
codesaver --list ./backups/project_2026-08-21_23-21-31.zip
codesaver --backup-now --exclude-pattern "*.tmp" --exclude-pattern "temp_*"

# Delete backups older than 30 days.
codesaver --backup-now --keep-days 30

# Include the contents reached through symbolic links.
codesaver --backup-now --follow-symlinks

# Exclude temporary and log files by extension.
codesaver --backup-now --exclude-ext .tmp --exclude-ext .log

# Preview files without creating an archive.
codesaver --project-dir ./my-project --dry-run

# Exclude a generated directory and verify the resulting ZIP.
codesaver --backup-now --exclude-dir generated --verify

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

The current stable binary is available in the [Desktop v1.1.1 release](https://github.com/vibecraft01/CodeSaver/releases/tag/desktop-v1.1.1):

- `CodeSaverDesktop-windows-x64.exe` for Windows.
- `CodeSaverDesktop-macos.zip` containing the macOS application.
- `CodeSaverDesktop-linux-amd64.deb` for Debian-based Linux distributions.

The stable [CLI v1.1.5 release](https://github.com/vibecraft01/CodeSaver/releases/tag/v1.1.5) is available.

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
