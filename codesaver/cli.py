"""Localized command-line interface for CodeSaver."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
from pathlib import Path
import subprocess
import shutil
import sys
import threading
import time
import tempfile
from datetime import datetime, timezone
from typing import Optional

from . import __version__
from .config import Config, load_config, normalize_extensions, parse_size
from .cloud import upload_archive
from .core import BackupError, BackupManager
from .lang import SUPPORTED_LANGUAGES, detect_language, normalize_language, translate
from .logging_utils import configure_logging
from .runtime import check_python_version, python_version_text

RECENT_PROJECTS_PATH = Path.home() / ".codesaver-recent.json"


class LocalizedArgumentParser(argparse.ArgumentParser):
    """ArgumentParser whose visible group labels follow the selected locale."""

    def __init__(self, language: str, *args: object, **kwargs: object) -> None:
        self.language = language
        super().__init__(*args, **kwargs)
        self._positionals.title = translate("arg.positional", language)
        self._optionals.title = translate("arg.options", language)

    def format_usage(self) -> str:
        usage = super().format_usage()
        return usage.replace("usage:", translate("arg.usage", self.language), 1)

    def format_help(self) -> str:
        help_text = super().format_help()
        help_text = help_text.replace("usage:", translate("arg.usage", self.language), 1)
        return help_text.replace("show this help message and exit", translate("help.help", self.language), 1)


def _language_from_argv(argv: Optional[list[str]]) -> Optional[str]:
    values = sys.argv[1:] if argv is None else argv
    for index, value in enumerate(values):
        if value.startswith("--language="):
            return normalize_language(value.split("=", 1)[1])
        if value == "--language" and index + 1 < len(values):
            return normalize_language(values[index + 1])
    return None


def build_parser(language: Optional[str] = None) -> argparse.ArgumentParser:
    language = normalize_language(language or detect_language())
    parser = LocalizedArgumentParser(language, add_help=False, description=translate("help.description", language))
    parser.add_argument("-h", "--help", action="help", help=translate("help.help", language))
    parser.add_argument("--project-dir", type=Path, default=None, help=translate("help.project_dir", language))
    parser.add_argument("--backup-dir", type=Path, default=None, help=translate("help.backup_dir", language))
    parser.add_argument("--interval", type=int, default=None, help=translate("help.interval", language))
    parser.add_argument("--no-autosave", action="store_true", help=translate("help.no_autosave", language))
    parser.add_argument("--backup-now", action="store_true", help=translate("help.backup_now", language))
    parser.add_argument("--dry-run", action="store_true", help=translate("help.dry_run", language))
    parser.add_argument("--verify", action="store_true", help=translate("help.verify", language))
    parser.add_argument("--manifest", action="store_true", help=translate("help.manifest", language))
    parser.add_argument("--list", type=Path, metavar="ARCHIVE", help=translate("help.list", language))
    parser.add_argument("--diff", type=Path, metavar="ARCHIVE", help=translate("help.diff", language))
    parser.add_argument("--health", action="store_true", help=translate("help.health", language))
    parser.add_argument("--stats", action="store_true", help=translate("help.stats", language))
    parser.add_argument("--git-context", action="store_true", help=translate("help.git_context", language))
    parser.add_argument("--checksum", type=Path, metavar="ARCHIVE", help=translate("help.checksum", language))
    parser.add_argument("--doctor", action="store_true", help=translate("help.doctor", language))
    parser.add_argument("--self-check", action="store_true", help="Verify the CodeSaver installation")
    parser.add_argument("--cleanup", action="store_true", help=translate("help.cleanup", language))
    parser.add_argument(
        "--exclude-dir", action="append", default=None, metavar="DIR", help=translate("help.exclude_dir", language)
    )
    parser.add_argument(
        "--exclude-pattern",
        action="append",
        default=None,
        metavar="PATTERN",
        help=translate("help.exclude_pattern", language),
    )
    parser.add_argument("--quiet", action="store_true", help=translate("help.quiet", language))
    parser.add_argument("--json", action="store_true", help=translate("help.json", language))
    parser.add_argument("--report", type=Path, metavar="FILE", help=translate("help.report", language))
    parser.add_argument(
        "--exclude-ext",
        action="append",
        default=None,
        metavar="EXT",
        help=translate("help.exclude_ext", language),
    )
    parser.add_argument("--compress", action="store_true", default=None, help=translate("help.compress", language))
    parser.add_argument("--max-size", metavar="SIZE", default=None, help=translate("help.max_size", language))
    parser.add_argument("--keep-last", type=int, default=None, metavar="N", help=translate("help.keep_last", language))
    parser.add_argument("--keep-days", type=int, default=None, metavar="N", help=translate("help.keep_days", language))
    parser.add_argument(
        "--follow-symlinks", action="store_true", default=None, help=translate("help.follow_symlinks", language)
    )
    parser.add_argument(
        "--no-gitignore", action="store_true", default=None, help=translate("help.no_gitignore", language)
    )
    parser.add_argument("--restore", type=Path, metavar="ARCHIVE", help=translate("help.restore", language))
    parser.add_argument("--restore-safe", action="store_true", help=translate("help.restore_safe", language))
    parser.add_argument("--archive-info", type=Path, metavar="ARCHIVE", help="Show archive metadata")
    parser.add_argument("--export-manifest", type=Path, metavar="ARCHIVE", help="Export archive file list")
    parser.add_argument("--delete-backup", type=Path, metavar="ARCHIVE", help="Delete one backup archive")
    parser.add_argument(
        "--rename-backup", nargs=2, type=Path, metavar=("ARCHIVE", "NEW_NAME"), help="Rename one backup archive"
    )
    parser.add_argument("--find", metavar="TEXT", help="Find files in the project by name")
    parser.add_argument("--list-backups", action="store_true", help="List all backups with metadata")
    parser.add_argument("--latest", action="store_true", help="Print the newest backup path")
    parser.add_argument("--storage-report", action="store_true", help="Summarize backed-up file extensions")
    parser.add_argument("--check-project", action="store_true", help="Check project files before creating a backup")
    parser.add_argument("--plan", action="store_true", help="Show the backup plan without creating an archive")
    parser.add_argument("--disk-check", action="store_true", help="Report free space at the backup destination")
    parser.add_argument("--verify-latest", action="store_true", help="Verify the newest backup archive")
    parser.add_argument("--file-report", action="store_true", help="Report project file counts and bytes by extension")
    parser.add_argument("--archive-members", type=Path, metavar="ARCHIVE", help="List archive members as JSON")
    parser.add_argument("--prune-preview", action="store_true", help="Preview backups eligible for cleanup")
    parser.add_argument("--git-diff-summary", action="store_true", help="Show changed Git files and line summary")
    parser.add_argument("--largest-files", type=int, metavar="N", help="Show the N largest project files")
    parser.add_argument("--changed-files", action="store_true", help="List files changed in the Git working tree")
    parser.add_argument("--archive-checksums", type=Path, metavar="ARCHIVE", help="Export archive member checksums")
    parser.add_argument("--config-show", action="store_true", help="Show effective backup configuration")
    parser.add_argument("--directory-report", action="store_true", help="Summarize project files by directory")
    parser.add_argument("--project-check", action="store_true", help="Check that the project directory is readable")
    parser.add_argument("--estimate-size", action="store_true", help="Estimate uncompressed backup size")
    parser.add_argument("--project-summary", action="store_true", help="Show a compact project summary")
    parser.add_argument("--archive-search", metavar="TEXT", help="Search backup archive names")
    parser.add_argument("--git-status-json", action="store_true", help="Export Git status as structured JSON")
    parser.add_argument("--export-inventory", type=Path, metavar="FILE", help="Export project inventory as CSV")
    parser.add_argument("--restore-preview", type=Path, metavar="ARCHIVE", help="Preview files in an archive")
    parser.add_argument("--gitignored-files", action="store_true", help="List files ignored by Git")
    parser.add_argument("--project-tree", action="store_true", help="Print a size-aware project tree")
    parser.add_argument("--search-content", metavar="TEXT", help="Search text in readable project files")
    parser.add_argument("--extension-report", action="store_true", help="Report file counts and bytes by extension")
    parser.add_argument("--health-report", action="store_true", help="Verify every archive with per-file results")
    parser.add_argument("--version", action="store_true", help="Print the CodeSaver version")
    parser.add_argument("--plan-json", type=Path, metavar="FILE", help="Write the backup plan as JSON")
    parser.add_argument("--verify-report", type=Path, metavar="FILE", help="Write archive verification results as JSON")
    parser.add_argument("--git-remote", action="store_true", help="Print configured Git remotes")
    parser.add_argument("--config-template", type=Path, metavar="FILE", help="Create a starter configuration file")
    parser.add_argument("--cloud-upload", type=Path, metavar="ARCHIVE", help="Upload an archive to a cloud endpoint")
    parser.add_argument("--cloud-url", metavar="URL", help="S3-compatible cloud upload endpoint")
    parser.add_argument("--cloud-token-env", default="CODESAVER_CLOUD_TOKEN", help="Token environment variable")
    parser.add_argument("--top-directories", type=int, metavar="N", help="Show the N largest project directories")
    parser.add_argument("--empty-directories", action="store_true", help="List empty project directories")
    parser.add_argument("--archive-age", type=Path, metavar="ARCHIVE", help="Show archive age in seconds")
    parser.add_argument("--archive-size", type=Path, metavar="ARCHIVE", help="Show one archive size")
    parser.add_argument("--git-branch", action="store_true", help="Print the current Git branch")
    parser.add_argument("--git-commit", action="store_true", help="Print the current Git commit")
    parser.add_argument("--excluded-paths", action="store_true", help="List configured exclusion rules")
    parser.add_argument("--backup-dir-check", action="store_true", help="Check backup directory access")
    parser.add_argument("--duplicates", action="store_true", help="Find duplicate project files by SHA-256")
    parser.add_argument("--recent-files", type=int, metavar="N", help="Show the N most recently modified files")
    parser.add_argument("--root-directories", action="store_true", help="Summarize top-level project directories")
    parser.add_argument("--git-log", type=int, metavar="N", help="Show the latest N Git commits")
    parser.add_argument("--verify-all", action="store_true", help="Verify every backup archive")
    parser.add_argument("--diff-latest", action="store_true", help="Compare the project with the newest backup")
    parser.add_argument("--unreadable-files", action="store_true", help="Find files that cannot be read")
    parser.add_argument("--file-types", action="store_true", help="Report project files grouped by extension")
    parser.add_argument("--stale-files", type=int, metavar="DAYS", help="List files not modified in the last N days")
    parser.add_argument("--archive-total", action="store_true", help="Show total bytes stored in backup archives")
    parser.add_argument("--git-tags", action="store_true", help="List Git tags in the project")
    parser.add_argument("--backup-index", action="store_true", help="Export a compact backup index")
    parser.add_argument(
        "--restore-files",
        nargs="+",
        metavar="ARCHIVE FILE",
        help=translate("help.restore_files", language),
    )
    parser.add_argument("--overwrite", action="store_true", help=translate("help.overwrite", language))
    parser.add_argument("--config", type=Path, metavar="FILE", help=translate("help.config", language))
    parser.add_argument("--log", type=Path, metavar="FILE", help=translate("help.log", language))
    parser.add_argument(
        "--language",
        choices=SUPPORTED_LANGUAGES,
        default=None,
        metavar=translate("help.language_choices", language),
        help=translate("help.language", language),
    )
    return parser


def _error_text(error: Exception, language: str) -> str:
    return error.localized(language) if isinstance(error, BackupError) else str(error)


def _format_duration(seconds: Optional[float], language: str) -> str:
    if seconds is None:
        return translate("message.eta_unknown", language)
    remaining = max(0, int(round(seconds)))
    hours, remainder = divmod(remaining, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def _progress_callback(language: str, quiet: bool = False):
    started: Optional[float] = None

    def show_progress(current: int, total: int, _path: Path, processed_bytes: int, total_bytes: int) -> None:
        if quiet:
            return
        nonlocal started
        now = time.monotonic()
        if started is None:
            started = now
        percent = 100.0 if total == 0 else current / total * 100
        elapsed = now - started
        if current >= total:
            eta = _format_duration(0, language)
        elif current and elapsed > 0:
            eta = _format_duration((total - current) * elapsed / current, language)
        else:
            eta = _format_duration(None, language)
        message = translate(
            "message.progress",
            language,
            current=current,
            total=total,
            percent=percent,
            processed_size=_format_bytes(processed_bytes),
            total_size=_format_bytes(total_bytes),
            eta=eta,
        )
        if sys.stdout.isatty():
            print("\r" + message, end="", flush=True)
            if current >= total:
                print()
        else:
            print(message)

    return show_progress


def _format_bytes(value: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}" if unit != "B" else f"{int(amount)} B"
        amount /= 1024
    return f"{value} B"


def _create_backup(
    manager: BackupManager,
    language: str,
    logger: logging.Logger,
    verify: bool = False,
    manifest: bool = False,
    quiet: bool = False,
    emit_messages: bool = True,
) -> Path:
    logger.info("Starting backup: project=%s backup_dir=%s", manager.project_dir, manager.backup_dir)
    archive = manager.create_backup(
        detailed_progress_callback=_progress_callback(language, quiet), include_manifest=manifest
    )
    if manager.last_cleanup_count:
        logger.info("Removed old backups: count=%s", manager.last_cleanup_count)
        if emit_messages:
            print(translate("message.backups_removed", language, count=manager.last_cleanup_count))
    logger.info("Backup created: %s", archive)
    if verify:
        members = manager.verify_backup(archive)
        logger.info("Backup verified: archive=%s members=%s", archive, members)
        if emit_messages:
            print(translate("message.backup_verified", language, count=members))
    if manifest:
        if emit_messages:
            print(translate("message.manifest_created", language, count=len(manager.list_files())))
    return archive


def _dry_run(manager: BackupManager, language: str) -> None:
    files = manager.list_files()
    total_size = 0
    for path in files:
        try:
            total_size += path.stat().st_size
        except OSError:
            continue
    print(translate("message.dry_run", language, count=len(files), size=_format_bytes(total_size)))
    for path in files:
        print(f"  {path.relative_to(manager.project_dir).as_posix()}")


def _write_backup_report(
    report_path: Path,
    manager: BackupManager,
    archive: Path,
    duration: float,
    verified: bool,
    manifest: bool,
) -> dict[str, object]:
    """Write a portable JSON summary that can be attached to CI artifacts."""
    files = manager.list_files()
    total_bytes = 0
    for path in files:
        try:
            total_bytes += path.stat().st_size
        except OSError:
            continue
    report: dict[str, object] = {
        "operation": "backup",
        "project": str(manager.project_dir),
        "archive": str(archive),
        "files": len(files),
        "total_bytes": total_bytes,
        "duration_seconds": round(duration, 3),
        "verified": verified,
        "manifest": manifest,
        "removed_old_backups": manager.last_cleanup_count,
    }
    report_path = report_path.expanduser()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _file_error_callback(language: str, logger: logging.Logger):
    def report(path: Path, error: BaseException) -> None:
        message = translate("message.file_skipped", language, path=path, error=error)
        logger.warning("File skipped: %s (%s)", path, error)
        print(message, file=sys.stderr)

    return report


def _load_recent_projects() -> list[Path]:
    try:
        raw = json.loads(RECENT_PROJECTS_PATH.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return []
        projects: list[Path] = []
        for value in raw:
            path = Path(str(value)).expanduser().resolve()
            if path.is_dir() and path not in projects:
                projects.append(path)
        return projects[:10]
    except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError):
        return []


def _remember_project(project_dir: Path) -> None:
    projects = [project_dir.resolve(), *_load_recent_projects()]
    unique: list[str] = []
    for path in projects:
        value = str(path)
        if value not in unique and Path(value).is_dir():
            unique.append(value)
    try:
        RECENT_PROJECTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        RECENT_PROJECTS_PATH.write_text(json.dumps(unique[:10], indent=2), encoding="utf-8")
    except OSError:
        pass


def _select_recent_project(language: str) -> Path:
    recent = _load_recent_projects()
    print(translate("recent.header", language))
    if recent:
        for index, path in enumerate(recent, start=1):
            print(f"{index}. {path}")
    else:
        print(translate("recent.none", language))
    print(f"c. {translate('recent.current', language)} ({Path.cwd().resolve()})")
    print(f"b. {translate('recent.browse', language)}")
    print(f"q. {translate('recent.quit', language)}")
    while True:
        try:
            choice = input(translate("recent.prompt", language)).strip().lower()
        except EOFError:
            return Path.cwd().resolve()
        if choice == "c" or choice == "":
            return Path.cwd().resolve()
        if choice == "b":
            value = input(translate("recent.path", language)).strip()
            path = Path(value).expanduser().resolve()
            if path.is_dir():
                return path
        elif choice == "q":
            raise KeyboardInterrupt
        elif choice.isdigit() and 1 <= int(choice) <= len(recent):
            return recent[int(choice) - 1]
        print(translate("recent.invalid", language))


def _autosave(
    manager: BackupManager, interval: int, stop: threading.Event, language: str, logger: logging.Logger
) -> None:
    while not stop.wait(interval):
        try:
            archive = _create_backup(manager, language, logger)
            print("\n" + translate("message.autosave_created", language, path=archive))
        except BackupError as exc:
            logger.error("Autosave failed: %s", _error_text(exc, language))
            print("\n" + translate("message.autosave_error", language, error=_error_text(exc, language)))


def run_menu(
    manager: BackupManager,
    autosave: bool = True,
    interval: int = 600,
    language: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
) -> None:
    language = normalize_language(language or detect_language())
    logger = logger or configure_logging(None)
    stop = threading.Event()
    worker = None
    if autosave:
        if interval <= 0:
            raise BackupError("errors.interval_positive")
        worker = threading.Thread(target=_autosave, args=(manager, interval, stop, language, logger), daemon=True)
        worker.start()
        print(translate("message.autosave_enabled", language, interval=interval))
    try:
        while True:
            print(
                "\n".join(
                    (
                        translate("menu.header", language),
                        translate("menu.backup", language),
                        translate("menu.restore", language),
                        translate("menu.exit", language),
                    )
                )
            )
            choice = input(translate("prompt.choice", language)).strip()
            try:
                if choice == "1":
                    print(translate("message.backup_created", language, path=_create_backup(manager, language, logger)))
                elif choice == "2":
                    archive = input(translate("prompt.archive", language)).strip()
                    count = manager.restore_backup(archive)
                    logger.info("Backup restored: archive=%s files=%s", archive, count)
                    print(translate("message.restore_completed", language, count=count))
                elif choice == "3":
                    return
                else:
                    print(translate("message.invalid_choice", language))
            except (BackupError, EOFError) as exc:
                logger.error("Menu operation failed: %s", _error_text(exc, language))
                print(translate("message.error", language, error=_error_text(exc, language)))
    except KeyboardInterrupt:
        print("\n" + translate("message.stopping", language))
    finally:
        stop.set()
        if worker:
            worker.join(timeout=1)


def _settings(args: argparse.Namespace, detected_language: str) -> tuple[Path, Config, str, logging.Logger]:
    project_dir = (args.project_dir or Path.cwd()).expanduser().resolve()
    config = load_config(args.config, project_dir)
    language = normalize_language(args.language or config.language or detected_language)
    interval = args.interval if args.interval is not None else config.interval
    if interval <= 0:
        raise BackupError("errors.interval_positive")
    try:
        max_size = parse_size(args.max_size if args.max_size is not None else config.max_size)
    except ValueError as exc:
        raise BackupError("errors.max_size_invalid", value=args.max_size) from exc
    keep_last = args.keep_last if args.keep_last is not None else config.keep_last
    if keep_last is not None and keep_last <= 0:
        raise BackupError("errors.keep_last_positive")
    keep_days = args.keep_days if args.keep_days is not None else config.keep_days
    if keep_days is not None and keep_days <= 0:
        raise BackupError("errors.keep_days_positive")
    try:
        excluded_extensions = normalize_extensions(
            args.exclude_ext if args.exclude_ext is not None else config.excluded_extensions
        )
    except ValueError as exc:
        raise BackupError("errors.exclude_ext_invalid", value=args.exclude_ext) from exc
    excluded_dirs = set(config.excluded_dirs)
    for value in args.exclude_dir or []:
        value = value.strip()
        if not value:
            raise BackupError("errors.exclude_dir_invalid")
        excluded_dirs.add(value)
    excluded_patterns = set(config.excluded_patterns)
    for value in args.exclude_pattern or []:
        value = value.strip()
        if not value:
            raise BackupError("errors.exclude_pattern_invalid")
        excluded_patterns.add(value)
    compress = config.compress if args.compress is None else args.compress
    use_gitignore = config.use_gitignore if args.no_gitignore is None else not args.no_gitignore
    effective = Config(
        interval=interval,
        language=language,
        backup_dir=args.backup_dir or config.backup_dir,
        log_path=args.log or config.log_path,
        excluded_dirs=frozenset(excluded_dirs),
        excluded_extensions=excluded_extensions,
        excluded_patterns=frozenset(excluded_patterns),
        compress=compress,
        max_size=max_size,
        keep_last=keep_last,
        keep_days=keep_days,
        follow_symlinks=config.follow_symlinks if args.follow_symlinks is None else args.follow_symlinks,
        use_gitignore=use_gitignore,
    )
    try:
        logger = configure_logging(effective.log_path)
    except OSError as exc:
        raise BackupError("errors.log_failed", error=exc) from exc
    return project_dir, effective, language, logger


def _health_check(manager: BackupManager, logger: logging.Logger) -> tuple[int, list[Path]]:
    """Verify every ZIP in the backup directory for CI and scheduled checks."""
    archives = sorted(manager.backup_dir.glob("*.zip"), key=lambda path: path.name)
    failed: list[Path] = []
    for archive in archives:
        try:
            manager.verify_backup(archive)
        except (BackupError, OSError, ValueError) as exc:
            failed.append(archive)
            logger.error("Backup health check failed: archive=%s error=%s", archive, exc)
    return len(archives), failed


def _backup_stats(manager: BackupManager) -> dict[str, object]:
    """Return a stable inventory summary for scripts and backup monitoring."""
    archives = sorted(manager.backup_dir.glob("*.zip"), key=lambda path: (path.stat().st_mtime, path.name))
    total_size = sum(path.stat().st_size for path in archives)
    return {
        "count": len(archives),
        "total_bytes": total_size,
        "newest": str(archives[-1]) if archives else None,
        "oldest": str(archives[0]) if archives else None,
    }


def _git_context(project_dir: Path) -> dict[str, object]:
    """Return Git metadata for automation without failing outside a repository."""
    try:

        def run(*args: str) -> str:
            return subprocess.check_output(
                ["git", "-C", str(project_dir), *args], stderr=subprocess.DEVNULL, text=True
            ).strip()

        return {
            "branch": run("branch", "--show-current") or "detached",
            "commit": run("rev-parse", "--short", "HEAD"),
            "dirty": bool(run("status", "--porcelain")),
        }
    except (OSError, subprocess.CalledProcessError):
        return {"branch": None, "commit": None, "dirty": False}


def _archive_checksum(archive: Path) -> str:
    digest = hashlib.sha256()
    with archive.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _doctor(manager: BackupManager) -> dict[str, object]:
    """Run safe environment checks before unattended backup jobs."""
    backup_dir = manager.backup_dir
    writable = False
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        probe = backup_dir / ".codesaver-write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        writable = True
    except OSError:
        writable = False
    return {
        "project_exists": manager.project_dir.is_dir(),
        "backup_directory": str(backup_dir),
        "backup_directory_writable": writable,
        "git": _git_context(manager.project_dir),
        "python": python_version_text(),
    }


def _self_check(manager: BackupManager) -> dict[str, object]:
    """Validate the installation and perform a disposable backup smoke test."""
    result = _doctor(manager)
    result["operation"] = "self-check"
    result["codesaver"] = __version__
    result["project_readable"] = False
    try:
        result["project_readable"] = all(path.is_file() and path.stat().st_size >= 0 for path in manager.list_files())
    except OSError:
        result["project_readable"] = False
    with tempfile.TemporaryDirectory(prefix="codesaver-check-") as temporary:
        test_project = Path(temporary) / "project"
        test_project.mkdir()
        (test_project / "codesaver-check.txt").write_text("CodeSaver installation check\n", encoding="utf-8")
        probe_manager = BackupManager(
            test_project,
            Path(temporary) / "backups",
        )
        try:
            archive = probe_manager.create_backup()
            result["test_backup"] = archive.is_file() and archive.stat().st_size > 0
        except (BackupError, OSError, ValueError):
            result["test_backup"] = False
    result["ok"] = all(
        (
            result["project_exists"],
            result["backup_directory_writable"],
            result["project_readable"],
            result["test_backup"],
        )
    )
    return result


def main(argv: Optional[list[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")
    raw_args = sys.argv[1:] if argv is None else argv
    detected_language = _language_from_argv(argv) or detect_language()
    if not check_python_version():
        print(translate("errors.python_version", detected_language, version=python_version_text()), file=sys.stderr)
        return 2
    args = build_parser(detected_language).parse_args(argv)
    language = normalize_language(args.language or detected_language)
    if not raw_args and args.project_dir is None:
        try:
            args.project_dir = _select_recent_project(language)
        except KeyboardInterrupt:
            print("\n" + translate("message.stopping", language))
            return 0
    logger: Optional[logging.Logger] = None
    try:
        project_dir, settings, language, logger = _settings(args, language)
        manager = BackupManager(
            project_dir,
            settings.backup_dir,
            excluded_dirs=set(settings.excluded_dirs),
            excluded_extensions=set(settings.excluded_extensions),
            excluded_patterns=set(settings.excluded_patterns),
            compress=settings.compress,
            max_size=settings.max_size,
            keep_last=settings.keep_last,
            keep_days=settings.keep_days,
            follow_symlinks=settings.follow_symlinks,
            use_gitignore=settings.use_gitignore,
            file_error_callback=_file_error_callback(language, logger),
        )
        _remember_project(project_dir)
        logger.info("CodeSaver started: language=%s project=%s", language, manager.project_dir)
        health_failed = False
        if args.version:
            print(__version__)
        elif args.plan_json:
            files = manager.list_files()
            plan = {
                "operation": "backup-plan",
                "project": str(manager.project_dir),
                "files": [
                    {"path": str(path.relative_to(manager.project_dir)), "bytes": path.stat().st_size} for path in files
                ],
                "file_count": len(files),
                "total_bytes": sum(path.stat().st_size for path in files),
            }
            target = args.plan_json.expanduser()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(
                json.dumps(
                    {"operation": "backup-plan", "file": str(target), "file_count": len(files)}, ensure_ascii=False
                )
                if args.json
                else f"Backup plan written: {target}"
            )
        elif args.verify_report:
            entries = []
            for archive in sorted(manager.backup_dir.glob("*.zip")):
                try:
                    entries.append({"archive": str(archive), "ok": True, "files": manager.verify_backup(archive)})
                except (BackupError, OSError, ValueError) as exc:
                    entries.append({"archive": str(archive), "ok": False, "error": str(exc)})
            target = args.verify_report.expanduser()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps({"operation": "verify-report", "archives": entries}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"Verification report written: {target}")
        elif args.git_remote:
            result = subprocess.run(
                ["git", "-C", str(manager.project_dir), "remote", "-v"], capture_output=True, text=True, check=False
            )
            remotes = result.stdout.splitlines()
            print(
                json.dumps({"operation": "git-remote", "remotes": remotes}, ensure_ascii=False, indent=2)
                if args.json
                else "\n".join(remotes)
            )
        elif args.config_template:
            target = args.config_template.expanduser()
            if target.exists():
                raise BackupError(f"Configuration file already exists: {target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            template = {
                "interval": 600,
                "language": "en",
                "backup_dir": "../code-saver-backups",
                "excluded_dirs": [".git", "__pycache__", ".venv", "build", "dist"],
                "exclude_ext": [".pyc", ".log", ".tmp"],
                "compress": True,
                "keep_last": 5,
                "use_gitignore": True,
            }
            target.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Configuration template written: {target}")
        elif args.gitignored_files:
            result = subprocess.run(
                ["git", "-C", str(manager.project_dir), "ls-files", "--others", "--ignored", "--exclude-standard"],
                capture_output=True,
                text=True,
                check=False,
            )
            files = result.stdout.splitlines()
            payload = {"operation": "gitignored-files", "files": files}
            print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else "\n".join(files))
        elif args.project_tree:
            tree = []
            for path in sorted(manager.list_files(), key=lambda item: str(item).lower()):
                tree.append(
                    {"path": str(path.relative_to(manager.project_dir).as_posix()), "bytes": path.stat().st_size}
                )
            print(
                json.dumps({"operation": "project-tree", "files": tree}, ensure_ascii=False, indent=2)
                if args.json
                else "\n".join(f"{_format_bytes(item['bytes']):>10}  {item['path']}" for item in tree)
            )
        elif args.search_content is not None:
            matches = []
            needle = args.search_content.casefold()
            for path in manager.list_files():
                try:
                    text = path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                for number, line in enumerate(text.splitlines(), start=1):
                    if needle in line.casefold():
                        matches.append(
                            {"path": str(path.relative_to(manager.project_dir)), "line": number, "text": line.strip()}
                        )
            print(
                json.dumps(
                    {"operation": "search-content", "query": args.search_content, "matches": matches},
                    ensure_ascii=False,
                    indent=2,
                )
                if args.json
                else "\n".join(f"{item['path']}:{item['line']}: {item['text']}" for item in matches)
            )
        elif args.extension_report:
            report: dict[str, dict[str, int]] = {}
            for path in manager.list_files():
                extension = path.suffix.lower() or "[no extension]"
                bucket = report.setdefault(extension, {"files": 0, "bytes": 0})
                bucket["files"] += 1
                bucket["bytes"] += path.stat().st_size
            print(
                json.dumps({"operation": "extension-report", "extensions": report}, ensure_ascii=False, indent=2)
                if args.json
                else "\n".join(
                    f"{key}: {value['files']} files, {_format_bytes(value['bytes'])}"
                    for key, value in sorted(report.items())
                )
            )
        elif args.health_report:
            entries = []
            for archive in sorted(manager.backup_dir.glob("*.zip")):
                try:
                    count = manager.verify_backup(archive)
                    entries.append({"archive": str(archive), "ok": True, "files": count})
                except (BackupError, OSError, ValueError) as exc:
                    entries.append({"archive": str(archive), "ok": False, "error": str(exc)})
            print(
                json.dumps({"operation": "health-report", "archives": entries}, ensure_ascii=False, indent=2)
                if args.json
                else "\n".join(f"{'OK' if item['ok'] else 'FAILED'}  {item['archive']}" for item in entries)
            )
        elif args.self_check:
            result = _self_check(manager)
            print(
                json.dumps(result, ensure_ascii=False, indent=2)
                if args.json
                else "Installation check: " + ("OK" if result["ok"] else "FAILED")
            )
            health_failed = not bool(result["ok"])
        elif args.cloud_upload:
            if not args.cloud_url:
                raise BackupError("--cloud-url is required with --cloud-upload")
            archive = args.cloud_upload.expanduser().resolve()
            status = upload_archive(archive, args.cloud_url, args.cloud_token_env)
            result = {"operation": "cloud-upload", "archive": str(archive), "status": status}
            print(
                json.dumps(result, ensure_ascii=False)
                if args.json
                else f"Cloud upload completed: {archive.name} (HTTP {status})"
            )
        elif args.project_summary:
            files = manager.list_files()
            total_bytes = sum(path.stat().st_size for path in files if path.is_file())
            extensions: dict[str, int] = {}
            for path in files:
                extension = path.suffix.lower() or "[no extension]"
                extensions[extension] = extensions.get(extension, 0) + 1
            result = {
                "operation": "project-summary",
                "files": len(files),
                "bytes": total_bytes,
                "extensions": extensions,
            }
            print(
                json.dumps(result, ensure_ascii=False, indent=2)
                if args.json
                else (
                    f"Files: {len(files)}\nSize: {_format_bytes(total_bytes)}\n"
                    f"Extensions: {', '.join(f'{key} ({value})' for key, value in sorted(extensions.items()))}"
                )
            )
        elif args.archive_search is not None:
            query = args.archive_search.casefold()
            matches = [path for path in sorted(manager.backup_dir.glob("*.zip")) if query in path.name.casefold()]
            result = {
                "operation": "archive-search",
                "query": args.archive_search,
                "archives": [str(path) for path in matches],
            }
            print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else "\n".join(result["archives"]))
        elif args.git_status_json:
            status = subprocess.run(
                ["git", "-C", str(manager.project_dir), "status", "--short"],
                capture_output=True,
                text=True,
                check=False,
            )
            entries = [{"status": line[:2], "path": line[3:]} for line in status.stdout.splitlines() if len(line) >= 4]
            result = {"operation": "git-status", "clean": not entries, "files": entries}
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.export_inventory:
            rows = []
            for path in manager.list_files():
                try:
                    stat = path.stat()
                except OSError:
                    continue
                rows.append(
                    (
                        str(path.relative_to(manager.project_dir)),
                        stat.st_size,
                        datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    )
                )
            target = args.export_inventory.expanduser()
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(("path", "bytes", "modified_utc"))
                writer.writerows(rows)
            result = {"operation": "export-inventory", "file": str(target), "files": len(rows)}
            print(
                json.dumps(result, ensure_ascii=False)
                if args.json
                else f"Inventory exported: {target} ({len(rows)} files)"
            )
        elif args.restore_preview:
            archive = args.restore_preview.expanduser().resolve()
            members = manager.list_backup(archive)
            result = {"operation": "restore-preview", "archive": str(archive), "files": members}
            print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else "\n".join(members))
        elif args.duplicates:
            hashes: dict[str, list[str]] = {}
            for path in manager.list_files():
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                hashes.setdefault(digest, []).append(str(path.relative_to(manager.project_dir)))
            result = {digest: paths for digest, paths in hashes.items() if len(paths) > 1}
            print(
                json.dumps({"operation": "duplicates", "groups": result}, ensure_ascii=False)
                if args.json
                else "\n".join("\n".join(paths) for paths in result.values())
            )
        elif args.recent_files:
            files = sorted(manager.list_files(), key=lambda path: path.stat().st_mtime, reverse=True)[
                : max(args.recent_files, 0)
            ]
            result = [
                {"path": str(path.relative_to(manager.project_dir)), "modified": path.stat().st_mtime} for path in files
            ]
            print(
                json.dumps({"operation": "recent-files", "files": result}, ensure_ascii=False)
                if args.json
                else "\n".join(item["path"] for item in result)
            )
        elif args.root_directories:
            totals: dict[str, int] = {}
            for path in manager.list_files():
                parts = path.relative_to(manager.project_dir).parts
                key = parts[0] if len(parts) > 1 else "."
                totals[key] = totals.get(key, 0) + path.stat().st_size
            print(
                json.dumps({"operation": "root-directories", "directories": totals}, ensure_ascii=False)
                if args.json
                else "\n".join(f"{key}: {_format_bytes(value)}" for key, value in sorted(totals.items()))
            )
        elif args.git_log:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(manager.project_dir),
                    "log",
                    f"-{max(args.git_log, 0)}",
                    "--pretty=format:%h %ad %s",
                    "--date=short",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            print(
                json.dumps({"operation": "git-log", "entries": result.stdout.splitlines()}, ensure_ascii=False)
                if args.json
                else result.stdout.rstrip()
            )
        elif args.verify_all:
            archives = sorted(manager.backup_dir.glob("*.zip"))
            failures = []
            for archive in archives:
                try:
                    manager.verify_backup(archive)
                except (BackupError, OSError, ValueError):
                    failures.append(str(archive))
            result = {
                "operation": "verify-all",
                "total": len(archives),
                "verified": len(archives) - len(failures),
                "failed": failures,
            }
            print(
                json.dumps(result, ensure_ascii=False)
                if args.json
                else f"Verified: {result['verified']}/{result['total']}"
            )
        elif args.diff_latest:
            archives = sorted(manager.backup_dir.glob("*.zip"), key=lambda path: path.stat().st_mtime, reverse=True)
            if not archives:
                raise BackupError("errors.archive_missing", archive=manager.backup_dir)
            diff = manager.compare_backup(archives[0])
            print(
                json.dumps({"operation": "diff-latest", "archive": str(archives[0]), **diff}, ensure_ascii=False)
                if args.json
                else f"Added: {len(diff['added'])}\nModified: {len(diff['modified'])}\nMissing: {len(diff['missing'])}"
            )
        elif args.unreadable_files:
            unreadable = []
            for path in manager.list_files():
                try:
                    with path.open("rb"):
                        pass
                except OSError:
                    unreadable.append(str(path.relative_to(manager.project_dir)))
            print(
                json.dumps({"operation": "unreadable-files", "files": unreadable}, ensure_ascii=False)
                if args.json
                else "\n".join(unreadable)
            )
        elif args.top_directories:
            totals: dict[Path, int] = {}
            for path in manager.list_files():
                directory = path.parent
                totals[directory] = totals.get(directory, 0) + path.stat().st_size
            items = sorted(totals.items(), key=lambda item: item[1], reverse=True)[: max(args.top_directories, 0)]
            result = [{"directory": str(path.relative_to(manager.project_dir)), "bytes": size} for path, size in items]
            print(
                json.dumps({"operation": "top-directories", "directories": result}, ensure_ascii=False)
                if args.json
                else "\n".join(f"{item['bytes']} bytes  {item['directory']}" for item in result)
            )
        elif args.empty_directories:
            directories = [path for path in manager.project_dir.rglob("*") if path.is_dir() and not any(path.iterdir())]
            result = [str(path.relative_to(manager.project_dir)) for path in directories]
            print(
                json.dumps({"operation": "empty-directories", "directories": result}, ensure_ascii=False)
                if args.json
                else "\n".join(result)
            )
        elif args.file_types:
            counts: dict[str, dict[str, int]] = {}
            for path in manager.list_files():
                suffix = path.suffix.lower() or "[no extension]"
                item = counts.setdefault(suffix, {"files": 0, "bytes": 0})
                item["files"] += 1
                item["bytes"] += path.stat().st_size
            result = {"operation": "file-types", "types": dict(sorted(counts.items()))}
            print(
                json.dumps(result, ensure_ascii=False)
                if args.json
                else "\n".join(
                    f"{suffix}: {item['files']} files, {_format_bytes(item['bytes'])}"
                    for suffix, item in result["types"].items()
                )
            )
        elif args.stale_files is not None:
            cutoff = time.time() - max(args.stale_files, 0) * 86400
            files = [path for path in manager.list_files() if path.stat().st_mtime < cutoff]
            result = {
                "operation": "stale-files",
                "days": args.stale_files,
                "files": [
                    {"path": str(path.relative_to(manager.project_dir)), "modified": path.stat().st_mtime}
                    for path in files
                ],
            }
            print(
                json.dumps(result, ensure_ascii=False)
                if args.json
                else "\n".join(item["path"] for item in result["files"])
            )
        elif args.archive_total:
            archives = sorted(manager.backup_dir.glob("*.zip"))
            total = sum(path.stat().st_size for path in archives)
            result = {"operation": "archive-total", "archives": len(archives), "bytes": total}
            print(json.dumps(result) if args.json else f"Archives: {len(archives)}\nTotal: {_format_bytes(total)}")
        elif args.git_tags:
            completed = subprocess.run(
                ["git", "-C", str(manager.project_dir), "tag", "--list"],
                capture_output=True,
                text=True,
                check=False,
            )
            tags = [line for line in completed.stdout.splitlines() if line]
            result = {"operation": "git-tags", "tags": tags}
            print(json.dumps(result, ensure_ascii=False) if args.json else "\n".join(tags))
        elif args.backup_index:
            archives = sorted(manager.backup_dir.glob("*.zip"), key=lambda path: path.stat().st_mtime, reverse=True)
            result = {
                "operation": "backup-index",
                "backups": [
                    {"path": str(path), "bytes": path.stat().st_size, "modified": path.stat().st_mtime}
                    for path in archives
                ],
            }
            print(
                json.dumps(result, ensure_ascii=False)
                if args.json
                else "\n".join(f"{item['bytes']} bytes  {item['path']}" for item in result["backups"])
            )
        elif args.archive_age:
            archive = args.archive_age.expanduser().resolve()
            age = max(0.0, datetime.now(timezone.utc).timestamp() - archive.stat().st_mtime)
            print(
                json.dumps({"operation": "archive-age", "archive": str(archive), "age_seconds": age})
                if args.json
                else f"Age: {int(age)} seconds"
            )
        elif args.archive_size:
            archive = args.archive_size.expanduser().resolve()
            size = archive.stat().st_size
            print(
                json.dumps({"operation": "archive-size", "archive": str(archive), "bytes": size})
                if args.json
                else f"Size: {_format_bytes(size)}"
            )
        elif args.git_branch or args.git_commit:
            key = "branch" if args.git_branch else "commit"
            value = _git_context(manager.project_dir).get(key)
            print(
                json.dumps({"operation": f"git-{key}", key: value}, ensure_ascii=False)
                if args.json
                else str(value or "")
            )
        elif args.excluded_paths:
            result = {
                "operation": "excluded-paths",
                "directories": sorted(manager.excluded_dirs),
                "extensions": sorted(manager.excluded_extensions),
                "patterns": sorted(manager.excluded_patterns),
            }
            print(json.dumps(result, ensure_ascii=False) if args.json else "\n".join(result["directories"]))
        elif args.backup_dir_check:
            manager.backup_dir.mkdir(parents=True, exist_ok=True)
            result = {"operation": "backup-dir-check", "path": str(manager.backup_dir), "writable": True}
            print(json.dumps(result, ensure_ascii=False) if args.json else f"Writable: yes\nPath: {manager.backup_dir}")
        elif args.largest_files:
            files = sorted(manager.list_files(), key=lambda path: path.stat().st_size, reverse=True)[
                : max(args.largest_files, 0)
            ]
            result = [
                {"path": str(path.relative_to(manager.project_dir)), "bytes": path.stat().st_size} for path in files
            ]
            print(
                json.dumps({"operation": "largest-files", "files": result}, ensure_ascii=False)
                if args.json
                else "\n".join(f"{item['bytes']} bytes  {item['path']}" for item in result)
            )
        elif args.changed_files:
            result = subprocess.run(
                ["git", "-C", str(manager.project_dir), "status", "--short"],
                capture_output=True,
                text=True,
                check=False,
            )
            print(
                json.dumps({"operation": "changed-files", "status": result.stdout}, ensure_ascii=False)
                if args.json
                else result.stdout.rstrip()
            )
        elif args.archive_checksums:
            import zipfile

            with zipfile.ZipFile(args.archive_checksums) as archive:
                checksums = {
                    info.filename: hashlib.sha256(archive.read(info)).hexdigest()
                    for info in archive.infolist()
                    if not info.is_dir()
                }
            print(
                json.dumps(
                    {"operation": "archive-checksums", "archive": str(args.archive_checksums), "files": checksums},
                    ensure_ascii=False,
                )
            )
        elif args.config_show:
            result = {
                "operation": "config",
                "project_dir": str(manager.project_dir),
                "backup_dir": str(manager.backup_dir),
                "keep_last": manager.keep_last,
                "keep_days": manager.keep_days,
                "use_gitignore": manager.use_gitignore,
            }
            print(
                json.dumps(result, ensure_ascii=False)
                if args.json
                else "\n".join(f"{key}: {value}" for key, value in result.items() if key != "operation")
            )
        elif args.directory_report:
            from collections import defaultdict

            report: dict[str, dict[str, int]] = defaultdict(lambda: {"files": 0, "bytes": 0})
            for path in manager.list_files():
                directory = str(path.parent.relative_to(manager.project_dir)) or "."
                report[directory]["files"] += 1
                report[directory]["bytes"] += path.stat().st_size
            print(
                json.dumps({"operation": "directory-report", "directories": report}, ensure_ascii=False)
                if args.json
                else "\n".join(
                    f"{key}: {value['files']} files, {_format_bytes(value['bytes'])}"
                    for key, value in sorted(report.items())
                )
            )
        elif args.project_check:
            files = manager.list_files()
            result = {
                "operation": "project-check",
                "project": str(manager.project_dir),
                "readable": True,
                "files": len(files),
            }
            print(json.dumps(result, ensure_ascii=False) if args.json else f"Readable: yes\nFiles: {len(files)}")
        elif args.estimate_size:
            total = sum(path.stat().st_size for path in manager.list_files())
            result = {"operation": "estimate-size", "bytes": total}
            print(json.dumps(result) if args.json else f"Estimated uncompressed size: {_format_bytes(total)}")
        elif args.disk_check:
            location = manager.backup_dir if manager.backup_dir.exists() else manager.backup_dir.parent
            free = shutil.disk_usage(location).free
            result = {"operation": "disk-check", "path": str(location), "free_bytes": free}
            print(json.dumps(result) if args.json else f"Free space at {location}: {_format_bytes(free)}")
        elif args.verify_latest:
            archives = sorted(manager.backup_dir.glob("*.zip"), key=lambda item: item.stat().st_mtime, reverse=True)
            if not archives:
                raise BackupError("errors.archive_missing", archive=manager.backup_dir)
            count = manager.verify_backup(archives[0])
            print(
                json.dumps({"operation": "verify-latest", "archive": str(archives[0]), "entries": count})
                if args.json
                else f"Verified: {archives[0]} ({count} entries)"
            )
        elif args.file_report:
            from collections import defaultdict

            report: dict[str, dict[str, int]] = defaultdict(lambda: {"files": 0, "bytes": 0})
            for path in manager.list_files():
                key = path.suffix.lower() or "[no extension]"
                report[key]["files"] += 1
                report[key]["bytes"] += path.stat().st_size
            print(
                json.dumps({"operation": "file-report", "extensions": report}, ensure_ascii=False)
                if args.json
                else "\n".join(
                    f"{key}: {value['files']} files, {_format_bytes(value['bytes'])}"
                    for key, value in sorted(report.items())
                )
            )
        elif args.archive_members:
            members = [item for item in manager.list_backup(args.archive_members) if not item.endswith("/")]
            print(
                json.dumps(
                    {"operation": "archive-members", "archive": str(args.archive_members), "members": members},
                    ensure_ascii=False,
                )
            )
        elif args.prune_preview:
            archives = sorted(manager.backup_dir.glob("*.zip"), key=lambda item: item.stat().st_mtime, reverse=True)
            keep = manager.keep_last or 0
            removable = archives[keep:] if keep else []
            print(
                json.dumps(
                    {"operation": "prune-preview", "removable": [str(path) for path in removable]}, ensure_ascii=False
                )
                if args.json
                else "\n".join(str(path) for path in removable)
            )
        elif args.git_diff_summary:
            result = subprocess.run(
                ["git", "-C", str(manager.project_dir), "diff", "--stat"], capture_output=True, text=True, check=False
            )
            print(
                json.dumps({"operation": "git-diff-summary", "summary": result.stdout}, ensure_ascii=False)
                if args.json
                else result.stdout.rstrip()
            )
        elif args.list_backups:
            archives = sorted(manager.backup_dir.glob("*.zip"), key=lambda item: item.stat().st_mtime, reverse=True)
            result = [{"archive": str(path), "size": path.stat().st_size} for path in archives]
            print(
                json.dumps({"operation": "list-backups", "backups": result}, ensure_ascii=False)
                if args.json
                else "\n".join(f"{item['archive']} ({item['size']} bytes)" for item in result)
            )
        elif args.latest:
            archives = sorted(manager.backup_dir.glob("*.zip"), key=lambda item: item.stat().st_mtime, reverse=True)
            latest = str(archives[0]) if archives else ""
            print(json.dumps({"operation": "latest", "archive": latest}) if args.json else latest)
        elif args.storage_report:
            from collections import Counter

            extensions = Counter(path.suffix.lower() or "[no extension]" for path in manager.list_files())
            print(
                json.dumps({"operation": "storage-report", "extensions": extensions}, ensure_ascii=False)
                if args.json
                else "\n".join(f"{key}: {value}" for key, value in sorted(extensions.items()))
            )
        elif args.check_project:
            files = manager.list_files()
            report = {
                "operation": "check-project",
                "files": len(files),
                "errors": len(manager.last_errors) if hasattr(manager, "last_errors") else 0,
            }
            print(json.dumps(report, ensure_ascii=False) if args.json else f"Project check: {report['files']} files")
        elif args.plan:
            files = manager.list_files()
            print(
                json.dumps(
                    {
                        "operation": "plan",
                        "project": str(manager.project_dir),
                        "files": len(files),
                        "backup_dir": str(manager.backup_dir),
                    },
                    ensure_ascii=False,
                )
                if args.json
                else f"Project: {manager.project_dir}\nFiles: {len(files)}\nBackup directory: {manager.backup_dir}"
            )
        elif args.archive_info:
            archive = args.archive_info.expanduser().resolve()
            members = [item for item in manager.list_backup(archive) if not item.endswith("/")]
            result = {
                "operation": "archive-info",
                "archive": str(archive),
                "size": archive.stat().st_size,
                "files": len(members),
            }
            print(
                json.dumps(result, ensure_ascii=False)
                if args.json
                else f"Archive: {archive}\nSize: {result['size']} bytes\nFiles: {result['files']}"
            )
        elif args.export_manifest:
            archive = args.export_manifest.expanduser().resolve()
            destination = archive.with_suffix(archive.suffix + ".manifest.txt")
            members = [item for item in manager.list_backup(archive) if not item.endswith("/")]
            destination.write_text("\n".join(members) + "\n", encoding="utf-8")
            print(
                json.dumps({"operation": "export-manifest", "manifest": str(destination), "files": len(members)})
                if args.json
                else f"Manifest written: {destination}"
            )
        elif args.delete_backup:
            archive = args.delete_backup.expanduser().resolve()
            archive.unlink()
            print(
                json.dumps({"operation": "delete-backup", "archive": str(archive)})
                if args.json
                else f"Deleted: {archive}"
            )
        elif args.rename_backup:
            archive, new_name = (item.expanduser().resolve() for item in args.rename_backup)
            target = archive.with_name(new_name.name + ("" if new_name.suffix else ".zip"))
            if target.exists():
                raise ValueError(f"Target already exists: {target}")
            archive.rename(target)
            print(
                json.dumps({"operation": "rename-backup", "archive": str(target)})
                if args.json
                else f"Renamed: {target}"
            )
        elif args.find:
            query = args.find.casefold()
            matches = [
                str(path.relative_to(manager.project_dir))
                for path in manager.list_files()
                if query in path.name.casefold()
            ]
            print(
                json.dumps({"operation": "find", "matches": matches}, ensure_ascii=False)
                if args.json
                else "\n".join(matches)
            )
        elif args.checksum:
            archive = args.checksum.expanduser().resolve()
            if not archive.is_file():
                raise BackupError("errors.archive_missing", archive=archive)
            checksum = _archive_checksum(archive)
            if args.json:
                print(json.dumps({"operation": "checksum", "archive": str(archive), "sha256": checksum}))
            else:
                print(f"SHA-256: {checksum}")
        elif args.doctor:
            report = _doctor(manager)
            if args.json:
                print(json.dumps({"operation": "doctor", **report}, ensure_ascii=False))
            else:
                print(translate("message.doctor", language, **report))
        elif args.git_context:
            context = _git_context(manager.project_dir)
            if args.json:
                print(json.dumps({"operation": "git-context", **context}, ensure_ascii=False))
            elif context["branch"]:
                print(translate("message.git_context", language, **context))
            else:
                print(translate("message.git_not_repo", language))
        elif args.stats:
            stats = _backup_stats(manager)
            if args.json:
                print(json.dumps({"operation": "stats", **stats}, ensure_ascii=False))
            else:
                print(
                    translate(
                        "message.stats_summary",
                        language,
                        count=stats["count"],
                        total_bytes=_format_bytes(int(stats["total_bytes"])),
                    )
                )
                if stats["newest"]:
                    print(translate("message.stats_newest", language, path=stats["newest"]))
                if stats["oldest"]:
                    print(translate("message.stats_oldest", language, path=stats["oldest"]))
        elif args.health:
            total, failed = _health_check(manager, logger)
            health_failed = bool(failed)
            if args.json:
                print(
                    json.dumps(
                        {
                            "operation": "health",
                            "total": total,
                            "verified": total - len(failed),
                            "failed": [str(path) for path in failed],
                        },
                        ensure_ascii=False,
                    )
                )
            else:
                print(
                    translate(
                        "message.health_summary",
                        language,
                        verified=total - len(failed),
                        total=total,
                    )
                )
                for archive in failed:
                    print(translate("message.health_failed", language, path=archive))
        elif args.list:
            members = manager.list_backup(args.list)
            print(translate("message.archive_contents", language, count=len(members)))
            for member in members:
                print(f"  {member}")
        elif args.diff:
            diff = manager.compare_backup(args.diff)
            if args.json:
                print(json.dumps({"operation": "diff", "archive": str(args.diff), **diff}, ensure_ascii=False))
            else:
                print(
                    translate(
                        "message.diff_summary",
                        language,
                        added=len(diff["added"]),
                        modified=len(diff["modified"]),
                        missing=len(diff["missing"]),
                    )
                )
                for key, label_key in (
                    ("added", "message.diff_added"),
                    ("modified", "message.diff_modified"),
                    ("missing", "message.diff_missing"),
                ):
                    if diff[key]:
                        print(translate(label_key, language) + ":")
                        for item in diff[key]:
                            print(f"  {item}")
        elif args.restore_files:
            archive, *members = args.restore_files
            count = manager.restore_files(archive, members, overwrite=args.overwrite)
            logger.info("Selected files restored: archive=%s files=%s", archive, count)
            if args.json:
                print(json.dumps({"operation": "restore-files", "archive": str(archive), "files": count}))
            else:
                print(translate("message.restore_files_completed", language, count=count))
        elif args.restore or args.restore_safe:
            if args.restore_safe and not args.restore:
                raise ValueError("--restore-safe requires --restore ARCHIVE")
            safety_archive = manager.create_backup() if args.restore_safe else None
            if args.verify:
                members = manager.verify_backup(args.restore)
                print(translate("message.backup_verified", language, count=members))
            count = manager.restore_backup(args.restore, overwrite=args.overwrite)
            logger.info("Backup restored: archive=%s files=%s", args.restore, count)
            if args.json:
                print(
                    json.dumps(
                        {
                            "operation": "restore",
                            "files": count,
                            "safety_backup": str(safety_archive) if safety_archive else None,
                        }
                    )
                )
            else:
                print(translate("message.restore_completed", language, count=count))
                if safety_archive:
                    print(translate("message.restore_safety_created", language, path=safety_archive))
        elif args.dry_run:
            _dry_run(manager, language)
        elif args.cleanup:
            removed = manager.cleanup_old_backups()
            if args.json:
                print(json.dumps({"operation": "cleanup", "removed": removed}))
            else:
                print(translate("message.cleanup", language, count=removed))
        elif args.backup_now:
            started = time.perf_counter()
            archive = _create_backup(
                manager,
                language,
                logger,
                args.verify,
                args.manifest,
                quiet=args.quiet or args.json,
                emit_messages=not args.json,
            )
            report = None
            if args.report:
                report = _write_backup_report(
                    args.report,
                    manager,
                    archive,
                    time.perf_counter() - started,
                    args.verify,
                    args.manifest,
                )
            if args.json:
                result = {
                    "operation": "backup",
                    "archive": str(archive),
                    "verified": args.verify,
                    "manifest": args.manifest,
                }
                if report:
                    result["report"] = str(args.report)
                print(json.dumps(result))
            elif not args.quiet:
                print(translate("message.backup_created", language, path=archive))
                if args.report:
                    print(f"Report written: {args.report}")
        else:
            run_menu(
                manager, autosave=not args.no_autosave, interval=settings.interval, language=language, logger=logger
            )
        if args.health and health_failed:
            return 1
        logger.info("CodeSaver finished successfully")
        return 0
    except (BackupError, OSError, ValueError) as exc:
        if logger:
            logger.error("CodeSaver failed: %s", _error_text(exc, language))
        print(translate("message.error", language, error=_error_text(exc, language)))
        return 1
