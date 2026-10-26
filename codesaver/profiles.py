"""Shared, validated backup-profile storage for CLI and Desktop."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Mapping

PROFILES_PATH = Path.home() / ".codesaver-profiles.json"
PROFILE_FIELDS = {
    "backup_dir",
    "excluded_dirs",
    "excluded_extensions",
    "excluded_patterns",
    "compress",
    "max_size",
    "keep_last",
    "keep_days",
    "follow_symlinks",
    "use_gitignore",
}
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,39}$")


class ProfileError(ValueError):
    """Invalid profile name or profile data."""


def _read(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProfileError(f"Cannot read profile store {path}: {exc}") from exc
    if not isinstance(data, dict) or any(not isinstance(v, dict) for v in data.values()):
        raise ProfileError(f"Invalid profile store: {path}")
    return data


def _validate_name(name: str) -> str:
    name = name.strip()
    if not _NAME.fullmatch(name):
        raise ProfileError("Profile name must be 1–40 characters and use letters, digits, spaces, '.', '_' or '-'.")
    return name


def list_profiles(path: Path = PROFILES_PATH) -> dict[str, dict[str, Any]]:
    """Return a copy of all named profiles."""
    return {name: dict(settings) for name, settings in _read(path).items()}


def get_profile(name: str, path: Path = PROFILES_PATH) -> dict[str, Any]:
    """Load a named profile or raise a helpful error."""
    name = _validate_name(name)
    profiles = _read(path)
    if name not in profiles:
        raise ProfileError(f"Profile not found: {name}")
    profile = profiles[name]
    unknown = set(profile) - PROFILE_FIELDS
    if unknown:
        raise ProfileError(f"Profile contains unsupported settings: {', '.join(sorted(unknown))}")
    _validate_settings(profile)
    return dict(profile)


def _validate_settings(profile: dict[str, Any]) -> None:
    if not isinstance(profile.get("compress", False), bool):
        raise ProfileError("Profile 'compress' must be true or false.")
    for key in ("excluded_dirs", "excluded_extensions", "excluded_patterns"):
        value = profile.get(key, [])
        if not isinstance(value, (list, tuple, set, frozenset)) or not all(
            isinstance(item, str) and item.strip() for item in value
        ):
            raise ProfileError(f"Profile '{key}' must be a list of non-empty strings.")
        profile[key] = sorted(set(value), key=str.casefold)
    for key in ("keep_last", "keep_days", "max_size"):
        value = profile.get(key)
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
            raise ProfileError(f"Profile '{key}' must be a non-negative integer or null.")
        if key in ("keep_last", "keep_days") and value == 0:
            raise ProfileError(f"Profile '{key}' must be positive or null.")
    for key in ("follow_symlinks", "use_gitignore"):
        if key in profile and not isinstance(profile[key], bool):
            raise ProfileError(f"Profile '{key}' must be true or false.")
    if profile.get("backup_dir") is not None and not isinstance(profile["backup_dir"], str):
        raise ProfileError("Profile 'backup_dir' must be a path string or null.")


def save_profile(name: str, settings: Mapping[str, Any], path: Path = PROFILES_PATH) -> None:
    """Validate and atomically save the backup-related portion of settings."""
    name = _validate_name(name)
    profile = {key: settings[key] for key in PROFILE_FIELDS if key in settings}
    _validate_settings(profile)

    profiles = _read(path)
    profiles[name] = profile
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, prefix=f"{path.name}.", suffix=".tmp", delete=False
        ) as stream:
            temporary = stream.name
            json.dump(profiles, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def delete_profile(name: str, path: Path = PROFILES_PATH) -> None:
    """Delete one named profile."""
    name = _validate_name(name)
    profiles = _read(path)
    if name not in profiles:
        raise ProfileError(f"Profile not found: {name}")
    del profiles[name]
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, prefix=f"{path.name}.", suffix=".tmp", delete=False
        ) as stream:
            temporary = stream.name
            json.dump(profiles, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
