"""Focused, safe inspection and extraction helpers for ZIP backups."""

from __future__ import annotations

import fnmatch
import hashlib
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath


def verify_zip(path: Path) -> dict[str, object]:
    """Read every member and report the first CRC failure, if any."""
    with zipfile.ZipFile(path) as archive:
        bad_member = archive.testzip()
        return {"archive": str(path), "valid": bad_member is None, "bad_member": bad_member}


def find_members(path: Path, pattern: str) -> list[str]:
    """Match archive paths against a case-insensitive glob pattern."""
    normalized_pattern = pattern.casefold()

    def matches(name: str) -> bool:
        name = name.casefold()
        return fnmatch.fnmatchcase(name, normalized_pattern) or (
            normalized_pattern.startswith("**/") and fnmatch.fnmatchcase(name, normalized_pattern[3:])
        )

    with zipfile.ZipFile(path) as archive:
        return sorted(info.filename for info in archive.infolist() if not info.is_dir() and matches(info.filename))


def extract_member(path: Path, member_name: str, destination: Path) -> Path:
    """Extract exactly one regular member, rejecting traversal and symlinks."""
    posix_name = PurePosixPath(member_name)
    windows_name = PureWindowsPath(member_name)
    if (
        not member_name
        or posix_name.is_absolute()
        or windows_name.is_absolute()
        or windows_name.drive
        or ".." in posix_name.parts
        or ".." in windows_name.parts
    ):
        raise ValueError("Unsafe archive member path")
    root = destination.expanduser().resolve()
    target = (root / Path(*posix_name.parts)).resolve()
    if target == root or root not in target.parents:
        raise ValueError("Archive member escapes destination")
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {target}")
    with zipfile.ZipFile(path) as archive:
        info = archive.getinfo(member_name)
        mode = info.external_attr >> 16
        if info.is_dir() or (mode & 0o170000) == 0o120000:
            raise ValueError("Only regular files can be extracted")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.read(info))
    return target


def compare_zips(first: Path, second: Path) -> dict[str, object]:
    """Compare two ZIPs by member name and SHA-256 content."""

    def hashes(path: Path) -> dict[str, str]:
        with zipfile.ZipFile(path) as archive:
            return {
                info.filename: hashlib.sha256(archive.read(info)).hexdigest()
                for info in archive.infolist()
                if not info.is_dir()
            }

    left, right = hashes(first), hashes(second)
    added = sorted(right.keys() - left.keys())
    removed = sorted(left.keys() - right.keys())
    changed = sorted(name for name in left.keys() & right.keys() if left[name] != right[name])
    return {"first": str(first), "second": str(second), "added": added, "removed": removed, "changed": changed}


def member_compression(path: Path) -> list[dict[str, object]]:
    """Report raw/stored bytes and savings for every regular member."""
    with zipfile.ZipFile(path) as archive:
        rows = []
        for info in archive.infolist():
            if info.is_dir():
                continue
            saved = info.file_size - info.compress_size
            rows.append(
                {
                    "path": info.filename,
                    "original_bytes": info.file_size,
                    "stored_bytes": info.compress_size,
                    "saved_bytes": saved,
                    "savings_percent": round(saved * 100 / info.file_size, 2) if info.file_size else 0.0,
                }
            )
        return rows
