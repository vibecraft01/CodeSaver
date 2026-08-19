"""JSON configuration loading for CodeSaver."""

from __future__ import annotations

import json
import os
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
    return Config(
        interval=interval,
        language=normalize_language(language) if language else None,
        backup_dir=_relative_path(raw.get("backup_dir"), config_path.parent, "backup_dir"),
        log_path=_relative_path(raw.get("log"), config_path.parent, "log"),
        excluded_dirs=frozenset(excluded),
    )
