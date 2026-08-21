"""Desktop settings and presentation helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import sys
from typing import Optional

from codesaver.config import normalize_extensions, parse_size
from codesaver.core import DEFAULT_EXCLUDED_DIRS

DESKTOP_CONFIG_PATH = Path.home() / ".codesaver-desktop.json"
DESKTOP_DEFAULT_EXCLUDED_DIRS = tuple(dict.fromkeys((*DEFAULT_EXCLUDED_DIRS, "node_modules", "dist", "build")))
DESKTOP_THEMES = ("system", "dark", "light", "midnight", "ocean", "forest", "high-contrast")
DESKTOP_LANGUAGES = ("auto", "ru", "en")


@dataclass
class DesktopSettings:
    """Persisted settings for the graphical application."""

    project_dir: Optional[str] = None
    backup_dir: Optional[str] = None
    excluded_dirs: tuple[str, ...] = DESKTOP_DEFAULT_EXCLUDED_DIRS
    excluded_extensions: tuple[str, ...] = ()
    interval_minutes: int = 10
    keep_last: int = 0
    language: str = "auto"
    theme: str = "system"
    accent_color: str = "#58A6FF"
    minimize_to_tray: bool = True
    compress: bool = True
    max_size: Optional[int] = None
    recent_projects: tuple[str, ...] = ()
    backup_on_start: bool = False

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
        recent_projects = tuple(
            str(Path(item).expanduser().resolve())
            for item in raw.get("recent_projects", [])
            if isinstance(item, str) and item
        )[:5]
        language = raw.get("language", "auto") if raw.get("language", "auto") in DESKTOP_LANGUAGES else "auto"
        theme = raw.get("theme", "system") if raw.get("theme", "system") in DESKTOP_THEMES else "system"
        accent_color = str(raw.get("accent_color", "#58A6FF"))
        if not _is_hex_color(accent_color):
            accent_color = "#58A6FF"
        return DesktopSettings(
            project_dir=_path_value(raw.get("project_dir")),
            backup_dir=_path_value(raw.get("backup_dir")),
            excluded_dirs=excluded_dirs or DESKTOP_DEFAULT_EXCLUDED_DIRS,
            excluded_extensions=excluded_extensions,
            interval_minutes=interval,
            keep_last=keep_last,
            language=language,
            theme=theme,
            accent_color=accent_color,
            minimize_to_tray=bool(raw.get("minimize_to_tray", True)),
            compress=bool(raw.get("compress", True)),
            max_size=max_size,
            recent_projects=recent_projects,
            backup_on_start=bool(raw.get("backup_on_start", False)),
        )
    except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError):
        return DesktopSettings()


def save_settings(settings: DesktopSettings, path: Path = DESKTOP_CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def detect_system_theme() -> str:
    """Return the Windows application theme as ``light`` or ``dark``.

    Windows stores the user preference in the Personalize registry key. On
    other platforms, or when the registry cannot be read, dark mode remains a
    safe deterministic fallback; users can still choose a fixed theme.
    """
    if os.name != "nt" and not sys.platform.startswith("win"):
        return "dark"
    try:
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return "light" if int(value) == 1 else "dark"
    except (ImportError, OSError, TypeError, ValueError):
        return "dark"


def detect_system_language() -> str:
    """Return the desktop UI language supported by the current locale."""
    candidates = []
    try:
        import locale

        candidates.append(locale.getlocale()[0])
    except (AttributeError, ValueError):
        pass
    candidates.extend((os.environ.get("LC_ALL"), os.environ.get("LANG"), os.environ.get("LANGUAGE")))
    for value in candidates:
        normalized = str(value or "").lower().replace("-", "_")
        if normalized.startswith("ru"):
            return "ru"
    return "en"


def _is_hex_color(value: str) -> bool:
    return len(value) == 7 and value.startswith("#") and all(char in "0123456789abcdefABCDEF" for char in value[1:])


def theme_colors(theme: str, accent: str = "#58A6FF") -> dict[str, str]:
    """Return a small, dependency-free color palette for the desktop UI."""
    palettes = {
        "dark": ("#0D1117", "#161B22", "#21262D", "#FFFFFF", "#30363D"),
        "light": ("#FFFFFF", "#F6F8FA", "#FFFFFF", "#1F2328", "#D0D7DE"),
        "midnight": ("#080B14", "#101629", "#17213A", "#E6EDF7", "#283653"),
        "ocean": ("#071A26", "#0B2B3A", "#123E50", "#E8FAFF", "#245A6D"),
        "forest": ("#0B1712", "#12251B", "#1B3525", "#E8F5EC", "#31543C"),
        "high-contrast": ("#000000", "#101010", "#202020", "#FFFFFF", "#FFFFFF"),
    }
    background, panel, button, text, border = palettes.get(theme, palettes["dark"])
    return {
        "background": background,
        "panel": panel,
        "button": button,
        "text": text,
        "border": border,
        "accent": accent,
    }


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
