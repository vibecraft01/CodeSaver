# Changelog

All notable CodeSaver changes are documented here.

## [Unreleased]

## [1.1.3] - 2026-08-20

- Added repeatable CLI `--exclude-ext` filtering for temporary, log, bytecode, and other file extensions.
- Added `exclude_ext` configuration support.
- Added localized help and errors for extension filtering.

## [Desktop 1.0.0] - 2026-08-20

- Added the optional PyQt5 CodeSaver Desktop application.
- Added project selection, project statistics, archive table, restore, progress, settings, autosave, themes, notifications, and system-tray support.
- Added local PyInstaller build scripts for Windows, macOS, and Linux `.deb` packages.

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
