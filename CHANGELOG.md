# Changelog

All notable CodeSaver changes are documented here.

## [Unreleased]

## [CLI 1.2.2] - 2026-08-24 (local)

- Added `--stats` to report backup count, total storage, and oldest/newest archives.
- Added machine-readable `--stats --json` output for monitoring and CI.

## [Desktop 1.0.9] - 2026-08-24 (local)

- Added a restore-safety comparison view for selected backups.
- Added added/modified/missing file reporting before restore.
- Added `Ctrl+D` to compare the selected archive quickly.

## [CLI 1.2.1] - 2026-08-24

- Added `--health` to verify every saved ZIP and report damaged archives.
- Added machine-readable health output with `--health --json`.
- Returns a non-zero exit code when any archive fails verification, making it suitable for CI and cron.

## [Desktop 1.0.8] - 2026-08-24

- Added optional automatic ZIP integrity verification after every backup.
- Added `Ctrl+Shift+V` to verify the selected backup quickly.
- Kept verification enabled by default for safer unattended backups.

## [CLI 1.2.0] - 2026-08-23

- Added `--diff ARCHIVE` to audit project drift against a ZIP backup.
- Added translated diff summaries and `--json` output for CI integrations.

## [Desktop 1.0.7] - 2026-08-23

- Added background verification for all saved archives.
- Added a verified/total backup health summary.
- Added a live countdown to the next autosave.

## [CLI 1.1.9] - 2026-08-23

- Added `--report FILE` to write an auditable JSON summary for CI pipelines and backup reviews.

## [Desktop 1.0.6] - 2026-08-23

- Added backup storage summary with archive count and total disk usage.
- Added archive context actions to copy a path or open its containing folder.
- Added `Ctrl+B`, `Ctrl+R`, and `F5` keyboard shortcuts for common actions.

## [CLI 1.1.8] - 2026-08-22

- Added `--quiet` for clean automation and CI output.
- Added `--json` backup results for scripts and integrations.

## [Desktop 1.0.5] - 2026-08-22

- Added manual backup-list refresh.
- Added automatic backup-list refresh every 30 seconds.

## [CLI 1.1.7] - 2026-08-22

- Added `--list ARCHIVE` to inspect a backup without restoring files.
- Added repeatable `--exclude-pattern` for command-line glob exclusions.
- Added validated archive listing and localized output for automation-friendly inspection.

## [Desktop 1.0.4] - 2026-08-22

- Added real-time backup archive search.
- Added background integrity verification for selected archives, including ZIP CRCs and SHA-256 manifests.
- Added clearer verification status and notification feedback.

## [CLI 1.1.6] - 2026-08-21

- Added optional SHA-256 manifests with `--manifest` for auditable backup contents.
- Extended `--verify` to validate manifest hashes as well as ZIP CRC integrity.
- Added localized manifest status messages and automated coverage for manifest creation and verification.

## [Desktop 1.0.3] - 2026-08-21

- Added customizable Midnight, Ocean, Forest, and High Contrast themes.
- Added a user-selectable accent color with a native color picker.
- Added automatic desktop-language detection with Russian and English UI options.
- Added an optional backup-on-start workflow for hands-off protection.
- Preserved recent projects when changing settings and expanded the settings model for future customization.

## [CLI 1.1.5] - 2026-08-21

- Added `--dry-run` to inspect files and total size without creating an archive.
- Added `--verify` to validate ZIP CRCs after backup creation or before restore.
- Added repeatable `--exclude-dir` command-line directory exclusions.
- Added clearer dry-run, verification, and operation summary messages.

## [Desktop 1.0.2] - 2026-08-21

- Added drag-and-drop project folder selection.
- Added a recent-project menu retaining up to five folders.
- Added explicit restore and old-backup cleanup confirmations.
- Added a 1 GB free-space warning before backup creation.
- Added backup percentage rendering in the system-tray icon.
- Added clearer reporting for files skipped because they could not be read.

## [CLI 1.1.4] - 2026-08-20

- Added ETA output to CLI backup progress messages.
- Added automatic Russian/English locale detection without requiring `--language`.
- Added JSON glob exclusion templates through `exclude_patterns` and wildcard values in `exclude_ext`.
- Added optional symlink traversal with `--follow-symlinks` and `follow_symlinks` configuration.
- Added recent-project selection when starting the CLI without arguments.
- Added per-file unreadable-file warnings while allowing the backup to continue.
- Added age-based cleanup with `--keep-days` and `keep_days` configuration.

## [Desktop 1.0.1] - 2026-08-20

- Added automatic Windows system-theme detection with a System theme option.
- Added immediate project file-count and total-size information when selecting a folder.
- Added smooth animated backup progress with percentage and byte totals.
- Added an Open Backups Folder action to the main window.
- Restored the last selected project automatically on application startup.

## [CLI 1.1.3] - 2026-08-20

- Added repeatable CLI `--exclude-ext` filtering for temporary, log, bytecode, and other file extensions.
- Added `exclude_ext` configuration support.
- Added localized help and errors for extension filtering.

## [Desktop 1.0.0] - 2026-08-20

- Added the optional PyQt5 CodeSaver Desktop application.
- Added project selection, project statistics, archive table, restore, progress, settings, autosave, themes, notifications, and system-tray support.
- Added local PyInstaller build scripts for Windows, macOS, and Linux `.deb` packages.
- Added the reproducible `CodeSaverDesktop.spec` PyInstaller configuration.

## [1.1.2] - 2026-08-19

- Added optional maximum ZIP compression with `--compress`.
- Added human-readable file-size filtering with `--max-size`.
- Added real-time progress totals for processed and total bytes.
- Added automatic old-backup cleanup with `--keep-last`.
- Added automatic root `.gitignore` filtering with optional `--no-gitignore` override.
- Added JSON configuration through `.codesaver.json` and `--config`.
- Added localized progress reporting for backup creation.
- Added optional file logging through `--log` or the `log` configuration key.
- Added explicit handling for missing paths, permission errors, invalid configuration, and damaged ZIP archives.
- Added Python 3.9+ runtime validation.
- Added broader backup, restore, exclusion, configuration, and localization tests.
- Added contributor guidance and optional Black/Flake8 development tooling.

## [1.1.0] - 2026-08-19

- Added GitHub Actions release builds for Windows, macOS, and Linux.
- Added platform installation scripts for Unix shells and Windows PowerShell.
- Added standalone console artifacts to GitHub Releases.

## [1.1.1] - 2026-08-19

- Switched the macOS release runner to `macos-latest` for reliable artifact delivery.

## [1.0.0]

- Initial cross-platform CodeSaver release.
- Timestamped ZIP backups, restore support, background autosave, localized CLI, and MIT licensing.
