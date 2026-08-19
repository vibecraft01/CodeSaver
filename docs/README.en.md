# CodeSaver

CodeSaver is a cross-platform command-line tool for creating timestamped ZIP snapshots of code projects. It uses Python's standard library, runs autosave in the background, and detects the system interface language.

## Quick start

```bash
python -m venv .venv
python -m pip install -e .
codesaver
```

Create one backup without opening the menu:

```bash
codesaver --project-dir ./my-project --backup-dir ./backups --backup-now
```

Restore an archive:

```bash
codesaver --project-dir ./my-project --restore ./backups/my-project_2026-01-20_14-30-00.zip --overwrite
```

The default autosave interval is 600 seconds. Use `--no-autosave` to disable it, `--interval 300` to change it, and `--language de` to override locale detection. `.git`, `__pycache__`, virtual environments, and tool caches are excluded by default.

CodeSaver also supports `.codesaver.json` configuration, progress output, optional logs (`--log ./codesaver.log`), and localized error messages for missing paths, permissions, invalid ZIP files, and invalid configuration. See the [main README](../README.md) for the complete documentation and real command examples. CodeSaver is released under the MIT License.
