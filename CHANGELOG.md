# Changelog

All notable CodeSaver changes are documented here.

## [Unreleased]

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
