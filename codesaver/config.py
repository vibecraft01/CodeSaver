"""JSON configuration loading for CodeSaver."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from .core import BackupError, DEFAULT_EXCLUDED_DIRS
from .lang import normalize_language

CONFIG_FILENAME = ".codesaver.json"


@dataclass(frozen=True)
class Config:
    """Validated settings loaded from a CodeSaver JSON file."""

    interval: int = 600
    language: Optional[str] = None
    backup_dir: Optional[Path] = None
    log_path: Optional[Path] = None
    excluded_dirs: frozenset[str] = DEFAULT_EXCLUDED_DIRS
    excluded_extensions: frozenset[str] = frozenset()
    compress: bool = False
    max_size: Optional[int] = None
    keep_last: Optional[int] = None
    use_gitignore: bool = True


_SIZE_UNITS = {
    "b": 1,
    "k": 1000,
    "kb": 1000,
    "m": 1000**2,
    "mb": 1000**2,
    "g": 1000**3,
    "gb": 1000**3,
    "t": 1000**4,
    "tb": 1000**4,
    "ki": 1024,
    "kib": 1024,
    "mi": 1024**2,
    "mib": 1024**2,
    "gi": 1024**3,
    "gib": 1024**3,
    "ti": 1024**4,
    "tib": 1024**4,
}


def parse_size(value: object) -> Optional[int]:
    """Parse bytes or a human-readable size such as ``100M`` or ``1GiB``."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("size must be a number")
    if isinstance(value, int):
        if value < 0:
            raise ValueError("size must be non-negative")
        return value
    if not isinstance(value, str):
        raise ValueError("size must be a number")
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([kmgt]?i?b?)?\s*", value.lower())
    if not match:
        raise ValueError("invalid size")
    number = float(match.group(1))
    unit = match.group(2) or "b"
    multiplier = _SIZE_UNITS.get(unit)
    if multiplier is None:
        raise ValueError("invalid size unit")
    return int(number * multiplier)


def normalize_extensions(values: object) -> frozenset[str]:
    """Normalize extension filters to lowercase values with a leading dot."""
    if values is None:
        return frozenset()
    if not isinstance(values, (list, tuple, set, frozenset)):
        raise ValueError("extensions must be a list")
    normalized: set[str] = set()
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("extension must be a non-empty string")
        for item in value.split(","):
            item = item.strip().lower()
            if item:
                normalized.add(item if item.startswith(".") else f".{item}")
    return frozenset(normalized)


def _relative_path(value: object, base_dir: Path, key: str) -> Optional[Path]:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise BackupError("errors.config_value", key=key)
    path_value = os.path.expanduser(value)
    if not os.path.isabs(path_value):
        path_value = os.path.join(str(base_dir), path_value)
    return Path(path_value).resolve()


def load_config(path: Optional[Union[Path, str]], project_dir: Path) -> Config:
    """Load an explicit config or ``.codesaver.json`` from the project root."""
    config_path = Path(path).expanduser().resolve() if path else project_dir / CONFIG_FILENAME
    if not config_path.exists():
        if path:
            raise BackupError("errors.config_not_found", path=config_path)
        return Config()
    if not config_path.is_file():
        raise BackupError("errors.config_value", key=str(config_path))
    try:
        with config_path.open("r", encoding="utf-8") as stream:
            raw = json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BackupError("errors.config_invalid", path=config_path, error=exc) from exc
    if not isinstance(raw, dict):
        raise BackupError("errors.config_invalid", path=config_path, error="root must be a JSON object")

    interval = raw.get("interval", 600)
    if isinstance(interval, bool) or not isinstance(interval, int) or interval <= 0:
        raise BackupError("errors.config_value", key="interval")
    language = raw.get("language")
    if language is not None and not isinstance(language, str):
        raise BackupError("errors.config_value", key="language")
    excluded = raw.get("excluded_dirs", list(DEFAULT_EXCLUDED_DIRS))
    if not isinstance(excluded, list) or not all(isinstance(item, str) and item for item in excluded):
        raise BackupError("errors.config_value", key="excluded_dirs")
    try:
        excluded_extensions = normalize_extensions(raw.get("exclude_ext", []))
    except ValueError as exc:
        raise BackupError("errors.config_value", key="exclude_ext") from exc
    compress = raw.get("compress", False)
    if not isinstance(compress, bool):
        raise BackupError("errors.config_value", key="compress")
    try:
        max_size = parse_size(raw.get("max_size"))
    except ValueError as exc:
        raise BackupError("errors.config_value", key="max_size") from exc
    keep_last = raw.get("keep_last")
    if isinstance(keep_last, bool) or (keep_last is not None and (not isinstance(keep_last, int) or keep_last < 1)):
        raise BackupError("errors.config_value", key="keep_last")
    use_gitignore = raw.get("use_gitignore", True)
    if not isinstance(use_gitignore, bool):
        raise BackupError("errors.config_value", key="use_gitignore")
    return Config(
        interval=interval,
        language=normalize_language(language) if language else None,
        backup_dir=_relative_path(raw.get("backup_dir"), config_path.parent, "backup_dir"),
        log_path=_relative_path(raw.get("log"), config_path.parent, "log"),
        excluded_dirs=frozenset(excluded),
        excluded_extensions=excluded_extensions,
        compress=compress,
        max_size=max_size,
        keep_last=keep_last,
        use_gitignore=use_gitignore,
    )
