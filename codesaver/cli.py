"""Localized command-line interface for CodeSaver."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys
import threading
from typing import Optional

from .config import Config, load_config, normalize_extensions, parse_size
from .core import BackupError, BackupManager
from .lang import SUPPORTED_LANGUAGES, detect_language, normalize_language, translate
from .logging_utils import configure_logging
from .runtime import check_python_version, python_version_text


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


def _progress_callback(language: str):
    def show_progress(current: int, total: int, _path: Path, processed_bytes: int, total_bytes: int) -> None:
        percent = 100.0 if total == 0 else current / total * 100
        message = translate(
            "message.progress",
            language,
            current=current,
            total=total,
            percent=percent,
            processed_size=_format_bytes(processed_bytes),
            total_size=_format_bytes(total_bytes),
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


def _create_backup(manager: BackupManager, language: str, logger: logging.Logger) -> Path:
    logger.info("Starting backup: project=%s backup_dir=%s", manager.project_dir, manager.backup_dir)
    archive = manager.create_backup(detailed_progress_callback=_progress_callback(language))
    if manager.last_cleanup_count:
        logger.info("Removed old backups: count=%s", manager.last_cleanup_count)
        print(translate("message.backups_removed", language, count=manager.last_cleanup_count))
    logger.info("Backup created: %s", archive)
    return archive


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
    try:
        excluded_extensions = normalize_extensions(
            args.exclude_ext if args.exclude_ext is not None else config.excluded_extensions
        )
    except ValueError as exc:
        raise BackupError("errors.exclude_ext_invalid", value=args.exclude_ext) from exc
    compress = config.compress if args.compress is None else args.compress
    use_gitignore = config.use_gitignore if args.no_gitignore is None else not args.no_gitignore
    effective = Config(
        interval=interval,
        language=language,
        backup_dir=args.backup_dir or config.backup_dir,
        log_path=args.log or config.log_path,
        excluded_dirs=config.excluded_dirs,
        excluded_extensions=excluded_extensions,
        compress=compress,
        max_size=max_size,
        keep_last=keep_last,
        use_gitignore=use_gitignore,
    )
    try:
        logger = configure_logging(effective.log_path)
    except OSError as exc:
        raise BackupError("errors.log_failed", error=exc) from exc
    return project_dir, effective, language, logger


def main(argv: Optional[list[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")
    detected_language = _language_from_argv(argv) or detect_language()
    if not check_python_version():
        print(translate("errors.python_version", detected_language, version=python_version_text()), file=sys.stderr)
        return 2
    args = build_parser(detected_language).parse_args(argv)
    language = normalize_language(args.language or detected_language)
    logger: Optional[logging.Logger] = None
    try:
        project_dir, settings, language, logger = _settings(args, language)
        manager = BackupManager(
            project_dir,
            settings.backup_dir,
            excluded_dirs=set(settings.excluded_dirs),
            excluded_extensions=set(settings.excluded_extensions),
            compress=settings.compress,
            max_size=settings.max_size,
            keep_last=settings.keep_last,
            use_gitignore=settings.use_gitignore,
        )
        logger.info("CodeSaver started: language=%s project=%s", language, manager.project_dir)
        if args.restore:
            count = manager.restore_backup(args.restore, overwrite=args.overwrite)
            logger.info("Backup restored: archive=%s files=%s", args.restore, count)
            print(translate("message.restore_completed", language, count=count))
        elif args.backup_now:
            print(translate("message.backup_created", language, path=_create_backup(manager, language, logger)))
        else:
            run_menu(
                manager, autosave=not args.no_autosave, interval=settings.interval, language=language, logger=logger
            )
        logger.info("CodeSaver finished successfully")
        return 0
    except (BackupError, ValueError) as exc:
        if logger:
            logger.error("CodeSaver failed: %s", _error_text(exc, language))
        print(translate("message.error", language, error=_error_text(exc, language)))
        return 1
