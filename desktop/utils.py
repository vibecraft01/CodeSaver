"""Desktop settings and presentation helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Optional

from codesaver.config import normalize_extensions, parse_size
from codesaver.core import DEFAULT_EXCLUDED_DIRS

DESKTOP_CONFIG_PATH = Path.home() / ".codesaver-desktop.json"
DESKTOP_DEFAULT_EXCLUDED_DIRS = tuple(dict.fromkeys((*DEFAULT_EXCLUDED_DIRS, "node_modules", "dist", "build")))


@dataclass
class DesktopSettings:
    """Persisted settings for the graphical application."""

    project_dir: Optional[str] = None
    backup_dir: Optional[str] = None
    excluded_dirs: tuple[str, ...] = DESKTOP_DEFAULT_EXCLUDED_DIRS
    excluded_extensions: tuple[str, ...] = ()
    interval_minutes: int = 10
    keep_last: int = 0
    language: str = "ru"
    theme: str = "dark"
    minimize_to_tray: bool = True
    compress: bool = True
    max_size: Optional[int] = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _path_value(value: object) -> Optional[str]:
    if value is None or value == "":
        return None
    return str(Path(str(value)).expanduser().resolve())


def load_settings(path: Path = DESKTOP_CONFIG_PATH) -> DesktopSettings:
    if not path.is_file():
        return DesktopSettings()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return DesktopSettings()
        excluded_dirs = tuple(str(item) for item in raw.get("excluded_dirs", DESKTOP_DEFAULT_EXCLUDED_DIRS))
        excluded_extensions = tuple(normalize_extensions(raw.get("excluded_extensions", [])))
        interval = max(0, int(raw.get("interval_minutes", 10)))
        keep_last = max(0, int(raw.get("keep_last", 0)))
        max_size = parse_size(raw.get("max_size"))
        language = raw.get("language", "ru") if raw.get("language", "ru") in {"ru", "en"} else "ru"
        theme = raw.get("theme", "dark") if raw.get("theme", "dark") in {"dark", "light"} else "dark"
        return DesktopSettings(
            project_dir=_path_value(raw.get("project_dir")),
            backup_dir=_path_value(raw.get("backup_dir")),
            excluded_dirs=excluded_dirs or DESKTOP_DEFAULT_EXCLUDED_DIRS,
            excluded_extensions=excluded_extensions,
            interval_minutes=interval,
            keep_last=keep_last,
            language=language,
            theme=theme,
            minimize_to_tray=bool(raw.get("minimize_to_tray", True)),
            compress=bool(raw.get("compress", True)),
            max_size=max_size,
        )
    except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError):
        return DesktopSettings()


def save_settings(settings: DesktopSettings, path: Path = DESKTOP_CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def format_bytes(value: int) -> str:
    amount = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if amount < 1024 or unit == "TB":
            return f"{int(amount)} {unit}" if unit == "B" else f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{value} B"


def archive_details(backup_dir: Path) -> list[tuple[Path, str, str]]:
    """Return archives sorted newest-first with display date and size."""
    archives = [path for path in backup_dir.glob("*.zip") if path.is_file()]
    archives.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return [
        (
            path,
            datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            format_bytes(path.stat().st_size),
        )
        for path in archives
    ]
