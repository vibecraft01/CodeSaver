"""Localized command-line interface for CodeSaver."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys
import threading
import time
from typing import Optional

from .config import Config, load_config, normalize_extensions, parse_size
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
        if args.health:
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
        elif args.restore:
            if args.verify:
                members = manager.verify_backup(args.restore)
                print(translate("message.backup_verified", language, count=members))
            count = manager.restore_backup(args.restore, overwrite=args.overwrite)
            logger.info("Backup restored: archive=%s files=%s", args.restore, count)
            print(translate("message.restore_completed", language, count=count))
        elif args.dry_run:
            _dry_run(manager, language)
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
