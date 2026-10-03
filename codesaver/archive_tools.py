"""Focused, safe inspection and extraction helpers for ZIP backups."""

from __future__ import annotations

import fnmatch
import hashlib
import re
import stat
import unicodedata
import zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Optional


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


def duplicate_contents(path: Path) -> list[list[str]]:
    """Return groups of archive paths whose uncompressed contents are identical."""
    by_digest: dict[str, list[str]] = defaultdict(list)
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if not info.is_dir():
                by_digest[hashlib.sha256(archive.read(info)).hexdigest()].append(info.filename)
    return sorted(sorted(names) for names in by_digest.values() if len(names) > 1)


def symlink_members(path: Path) -> list[dict[str, str]]:
    """List symbolic-link entries recorded in ZIP Unix attributes."""
    with zipfile.ZipFile(path) as archive:
        return [
            {"path": info.filename, "target": archive.read(info).decode("utf-8", errors="replace")}
            for info in archive.infolist()
            if stat.S_ISLNK(info.external_attr >> 16)
        ]


def member_permissions(path: Path) -> list[dict[str, object]]:
    """Report the Unix mode bits stored for every archive entry."""
    with zipfile.ZipFile(path) as archive:
        results = []
        for info in archive.infolist():
            mode = info.external_attr >> 16
            results.append(
                {
                    "path": info.filename,
                    "mode_octal": format(stat.S_IMODE(mode), "04o") if mode else None,
                    "kind": "symlink" if stat.S_ISLNK(mode) else "directory" if info.is_dir() else "file",
                }
            )
        return results


def members_in_date_range(path: Path, start: date, end: date) -> list[dict[str, object]]:
    """List files with ZIP timestamps falling on inclusive calendar dates."""
    if end < start:
        raise ValueError("End date must not precede start date")
    with zipfile.ZipFile(path) as archive:
        return [
            {"path": info.filename, "timestamp": datetime(*info.date_time).isoformat(sep=" ")}
            for info in archive.infolist()
            if not info.is_dir() and start <= date(*info.date_time[:3]) <= end
        ]


def members_larger_than(path: Path, minimum_bytes: int) -> list[dict[str, object]]:
    """List files whose uncompressed size is strictly above a byte threshold."""
    if minimum_bytes < 0:
        raise ValueError("Minimum size must be non-negative")
    with zipfile.ZipFile(path) as archive:
        return [
            {"path": info.filename, "bytes": info.file_size}
            for info in archive.infolist()
            if not info.is_dir() and info.file_size > minimum_bytes
        ]


def duplicate_member_paths(path: Path) -> list[dict[str, object]]:
    """Report repeated non-directory names stored more than once in a ZIP."""
    names: dict[str, list[int]] = defaultdict(list)
    with zipfile.ZipFile(path) as archive:
        for index, info in enumerate(archive.infolist()):
            if not info.is_dir():
                names[info.filename].append(index)
    return [{"path": name, "entries": indexes} for name, indexes in sorted(names.items()) if len(indexes) > 1]


def case_colliding_paths(path: Path) -> list[list[str]]:
    """Find distinct member paths that collide under case-insensitive filesystems."""
    names: dict[str, set[str]] = defaultdict(set)
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if not info.is_dir():
                names[info.filename.casefold()].add(info.filename)
    return sorted(sorted(group) for group in names.values() if len(group) > 1)


def encrypted_members(path: Path) -> list[str]:
    """List members marked as encrypted by the ZIP general-purpose flag."""
    with zipfile.ZipFile(path) as archive:
        return sorted(info.filename for info in archive.infolist() if not info.is_dir() and info.flag_bits & 0x1)


def compression_methods(path: Path) -> list[dict[str, object]]:
    """Summarize archive compression methods and their stored/raw byte totals."""
    labels = {
        zipfile.ZIP_STORED: "stored",
        zipfile.ZIP_DEFLATED: "deflate",
        zipfile.ZIP_BZIP2: "bzip2",
        zipfile.ZIP_LZMA: "lzma",
    }
    if hasattr(zipfile, "ZIP_ZSTANDARD"):
        labels[getattr(zipfile, "ZIP_ZSTANDARD")] = "zstandard"
    methods: dict[int, dict[str, int]] = defaultdict(lambda: {"files": 0, "original_bytes": 0, "stored_bytes": 0})
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            record = methods[info.compress_type]
            record["files"] += 1
            record["original_bytes"] += info.file_size
            record["stored_bytes"] += info.compress_size
    return [
        {"method_id": method_id, "method": labels.get(method_id, "unknown"), **values}
        for method_id, values in sorted(methods.items())
    ]


def high_ratio_members(path: Path, minimum_ratio: float) -> list[dict[str, object]]:
    """List files whose uncompressed/compressed ratio meets a threshold."""
    if minimum_ratio <= 0:
        raise ValueError("Minimum compression ratio must be greater than zero")
    results = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir() or info.compress_size <= 0:
                continue
            ratio = info.file_size / info.compress_size
            if ratio >= minimum_ratio:
                results.append(
                    {
                        "path": info.filename,
                        "ratio": round(ratio, 2),
                        "original_bytes": info.file_size,
                        "stored_bytes": info.compress_size,
                    }
                )
    return sorted(results, key=lambda item: (-float(item["ratio"]), str(item["path"])))


def portable_path_issues(path: Path) -> list[dict[str, object]]:
    """Find ZIP member names likely to fail or change meaning on Windows."""
    reserved = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?$", re.IGNORECASE)
    invalid_chars = set('<>:"|?*')
    issues = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            name = info.filename.rstrip("/")
            win_path = PureWindowsPath(name)
            reasons = []
            if win_path.drive or win_path.is_absolute() or name.startswith(("/", "\\")):
                reasons.append("absolute-or-drive-path")
            for part in re.split(r"[/\\]", name):
                if part in {"", ".", ".."}:
                    if part == "..":
                        reasons.append("parent-traversal")
                    continue
                if any(character in invalid_chars or ord(character) < 32 for character in part):
                    reasons.append("windows-invalid-character")
                if part.endswith((".", " ")):
                    reasons.append("trailing-dot-or-space")
                if reserved.fullmatch(part):
                    reasons.append("reserved-device-name")
            if reasons:
                issues.append({"path": info.filename, "issues": sorted(set(reasons))})
    return issues


def unicode_name_collisions(path: Path) -> list[list[str]]:
    """Find paths identical after Unicode NFC normalization and case folding."""
    groups: dict[str, set[str]] = defaultdict(set)
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if not info.is_dir():
                groups[unicodedata.normalize("NFC", info.filename).casefold()].add(info.filename)
    return sorted(sorted(group) for group in groups.values() if len(group) > 1)


def archive_depth_report(path: Path) -> dict[str, object]:
    """Summarize non-directory members by path depth and identify deepest paths."""
    counts: dict[int, int] = defaultdict(int)
    members: list[tuple[int, str]] = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            depth = len([part for part in re.split(r"[/\\]", info.filename) if part])
            counts[depth] += 1
            members.append((depth, info.filename))
    maximum = max(counts, default=0)
    return {
        "max_depth": maximum,
        "files_by_depth": {str(depth): counts[depth] for depth in sorted(counts)},
        "deepest_members": sorted(name for depth, name in members if depth == maximum),
    }


def unsafe_symlink_targets(path: Path) -> list[dict[str, str]]:
    """Flag symlinks with absolute, drive-qualified, or parent-traversing targets."""
    results = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if not stat.S_ISLNK(info.external_attr >> 16):
                continue
            target = archive.read(info).decode("utf-8", errors="replace")
            posix_target = PurePosixPath(target)
            windows_target = PureWindowsPath(target)
            if (
                posix_target.is_absolute()
                or windows_target.is_absolute()
                or windows_target.drive
                or ".." in posix_target.parts
                or ".." in windows_target.parts
            ):
                results.append({"path": info.filename, "target": target})
    return results


def file_directory_conflicts(path: Path) -> list[dict[str, str]]:
    """Find files whose names are also required as parent directories."""
    files: set[str] = set()
    parents: dict[str, str] = {}
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            normalized = "/".join(part for part in re.split(r"[/\\]", info.filename) if part)
            if not normalized:
                continue
            if not info.is_dir():
                files.add(normalized)
            parts = normalized.split("/")
            for index in range(1, len(parts)):
                parent = "/".join(parts[:index])
                parents[parent] = normalized
    return [{"file": name, "child": parents[name]} for name in sorted(files & parents.keys())]


def archive_path_length_report(path: Path, limit: int = 240) -> dict[str, object]:
    """Summarize member-name lengths and list paths beyond a portability limit."""
    if limit < 1:
        raise ValueError("Path length limit must be positive")
    with zipfile.ZipFile(path) as archive:
        rows = [
            {"path": info.filename, "characters": len(info.filename), "utf8_bytes": len(info.filename.encode("utf-8"))}
            for info in archive.infolist()
            if not info.is_dir()
        ]
    return {
        "limit": limit,
        "maximum_characters": max((int(row["characters"]) for row in rows), default=0),
        "long_paths": [row for row in rows if int(row["characters"]) > limit],
        "files": len(rows),
    }


def archive_root_layout(path: Path) -> dict[str, object]:
    """Summarize top-level folders and members stored directly at the archive root."""
    roots: dict[str, int] = defaultdict(int)
    loose: list[str] = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            parts = [part for part in re.split(r"[/\\]", info.filename) if part]
            if len(parts) < 2:
                loose.append(info.filename)
            else:
                roots[parts[0]] += 1
    return {"root_folders": dict(sorted(roots.items())), "loose_files": sorted(loose), "folder_count": len(roots)}


def archive_comment_report(path: Path) -> dict[str, object]:
    """Return archive-level and per-member comments with their byte lengths."""
    with zipfile.ZipFile(path) as archive:
        global_comment_bytes = len(archive.comment)
        global_comment = archive.comment.decode("utf-8", errors="replace")
        member_comments = [
            {
                "path": info.filename,
                "comment": info.comment.decode("utf-8", errors="replace"),
                "bytes": len(info.comment),
            }
            for info in archive.infolist()
            if info.comment
        ]
    return {
        "archive_comment": global_comment,
        "archive_comment_bytes": global_comment_bytes,
        "member_comments": member_comments,
    }


def archive_crc_inventory(path: Path) -> list[dict[str, object]]:
    """List stored CRC-32 checksums without reading/decompressing member data."""
    with zipfile.ZipFile(path) as archive:
        return [
            {"path": info.filename, "crc32": f"{info.CRC:08x}", "bytes": info.file_size}
            for info in archive.infolist()
            if not info.is_dir()
        ]


def archive_timestamp_summary(path: Path) -> dict[str, object]:
    """Summarize member timestamps by year and identify oldest/newest entries."""
    by_year: dict[str, int] = defaultdict(int)
    members: list[tuple[datetime, str]] = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            timestamp = datetime(*info.date_time)
            by_year[str(timestamp.year)] += 1
            members.append((timestamp, info.filename))
    ordered = sorted(members)
    return {
        "files_by_year": dict(sorted(by_year.items())),
        "oldest": {"path": ordered[0][1], "timestamp": ordered[0][0].isoformat(sep=" ")} if ordered else None,
        "newest": {"path": ordered[-1][1], "timestamp": ordered[-1][0].isoformat(sep=" ")} if ordered else None,
    }


def duplicate_member_basenames(path: Path) -> list[dict[str, object]]:
    """Group distinct archive paths that share the same final filename."""
    names: dict[str, set[str]] = defaultdict(set)
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            basename = re.split(r"[/\\]", info.filename.rstrip("/\\"))[-1].casefold()
            names[basename].add(info.filename)
    return [{"basename": name, "paths": sorted(paths)} for name, paths in sorted(names.items()) if len(paths) > 1]


def hidden_members(path: Path) -> list[str]:
    """List entries hidden by dot-prefixed path components or the DOS hidden flag."""
    with zipfile.ZipFile(path) as archive:
        return sorted(
            info.filename
            for info in archive.infolist()
            if not info.is_dir()
            and (
                any(part.startswith(".") for part in re.split(r"[/\\]", info.filename) if part)
                or bool(info.external_attr & 0x02)
            )
        )


def mixed_separator_members(path: Path) -> list[str]:
    """List member names containing backslashes in their raw ZIP local headers."""
    with zipfile.ZipFile(path) as archive:
        names = []
        for info in archive.infolist():
            archive.fp.seek(info.header_offset)
            header = archive.fp.read(30)
            filename_length = int.from_bytes(header[26:28], "little")
            raw_name = archive.fp.read(filename_length)
            if b"\\" in raw_name:
                encoding = "utf-8" if info.flag_bits & 0x800 else "cp437"
                names.append(raw_name.decode(encoding, errors="replace"))
        return sorted(names)


def executable_members(path: Path) -> list[dict[str, str]]:
    """List members carrying Unix executable permission bits."""
    with zipfile.ZipFile(path) as archive:
        return [
            {"path": info.filename, "mode_octal": format(stat.S_IMODE(info.external_attr >> 16), "04o")}
            for info in archive.infolist()
            if not info.is_dir()
            and not stat.S_ISLNK(info.external_attr >> 16)
            and stat.S_IMODE(info.external_attr >> 16) & 0o111
        ]


def empty_directory_members(path: Path) -> list[str]:
    """List explicit ZIP directory entries that contain no archived descendants."""
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
    directories = {info.filename.rstrip("/") for info in entries if info.is_dir()}
    files = [info.filename for info in entries if not info.is_dir()]
    return sorted(
        directory
        for directory in directories
        if not any(name.startswith(directory + "/") or name.startswith(directory + "\\") for name in files)
        and not any(
            other != directory and (other.startswith(directory + "/") or other.startswith(directory + "\\"))
            for other in directories
        )
    )


def unicode_control_names(path: Path) -> list[dict[str, object]]:
    """Find member names containing control or formatting characters, including bidi controls."""
    results = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            suspicious = [
                {
                    "character": character,
                    "codepoint": f"U+{ord(character):04X}",
                    "category": unicodedata.category(character),
                    "name": unicodedata.name(character, "UNNAMED"),
                }
                for character in info.filename
                if unicodedata.category(character) in {"Cc", "Cf", "Cs"}
            ]
            if suspicious:
                results.append({"path": info.filename, "characters": suspicious})
    return results


def long_path_components(path: Path, limit: int = 255) -> list[dict[str, object]]:
    """Find individual path components longer than a filesystem portability limit."""
    if limit < 1:
        raise ValueError("Component length limit must be positive")
    results = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            for component in re.split(r"[/\\]", info.filename):
                if len(component) > limit:
                    results.append(
                        {
                            "path": info.filename,
                            "component": component,
                            "characters": len(component),
                            "utf8_bytes": len(component.encode("utf-8")),
                        }
                    )
    return results


def duplicate_directory_entries(path: Path) -> list[dict[str, object]]:
    """Report repeated explicit directory records, including their ZIP entry indexes."""
    indexes: dict[str, list[int]] = defaultdict(list)
    with zipfile.ZipFile(path) as archive:
        for index, info in enumerate(archive.infolist()):
            if info.is_dir():
                indexes[info.filename.rstrip("/\\")].append(index)
    return [{"path": name, "entries": positions} for name, positions in sorted(indexes.items()) if len(positions) > 1]


def unsupported_compression_members(path: Path) -> list[dict[str, object]]:
    """List members using a compression method unsupported by this Python runtime."""
    supported = {
        zipfile.ZIP_STORED,
        zipfile.ZIP_DEFLATED,
        zipfile.ZIP_BZIP2,
        zipfile.ZIP_LZMA,
    }
    if hasattr(zipfile, "ZIP_ZSTANDARD"):
        supported.add(getattr(zipfile, "ZIP_ZSTANDARD"))
    with zipfile.ZipFile(path) as archive:
        return [
            {"path": info.filename, "method_id": info.compress_type}
            for info in archive.infolist()
            if not info.is_dir() and info.compress_type not in supported
        ]


def member_type_conflicts(path: Path) -> list[dict[str, str]]:
    """Find names whose trailing-slash directory marker conflicts with Unix type bits."""
    results = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            mode = info.external_attr >> 16
            unix_type = stat.S_IFMT(mode)
            if not unix_type:
                continue
            is_unix_directory = unix_type == stat.S_IFDIR
            if is_unix_directory != info.is_dir():
                results.append(
                    {
                        "path": info.filename,
                        "name_type": "directory" if info.is_dir() else "file",
                        "unix_type": "directory" if is_unix_directory else "non-directory",
                    }
                )
    return results


def absolute_member_paths(path: Path) -> list[str]:
    """Find ZIP members whose names are rooted or carry a Windows drive prefix."""
    with zipfile.ZipFile(path) as archive:
        return sorted(
            info.filename.replace("\\", "/")
            for info in archive.infolist()
            if PurePosixPath(info.filename.replace("\\", "/")).is_absolute()
            or PureWindowsPath(info.filename).is_absolute()
            or bool(PureWindowsPath(info.filename).drive)
        )


def unicode_compatibility_collisions(path: Path) -> list[list[str]]:
    """Find distinct member paths that collide after Unicode NFKC and case folding."""
    grouped: dict[str, set[str]] = defaultdict(set)
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            normalized = unicodedata.normalize("NFKC", info.filename).casefold()
            grouped[normalized].add(info.filename)
    return [sorted(names) for _, names in sorted(grouped.items()) if len(names) > 1]


def extra_field_audit(path: Path) -> list[dict[str, object]]:
    """Report repeated ZIP extra-field identifiers without unpacking member data."""
    issues = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            offset = 0
            identifiers: list[int] = []
            while offset < len(info.extra):
                if len(info.extra) - offset < 4:
                    break
                field_id = int.from_bytes(info.extra[offset : offset + 2], "little")
                field_length = int.from_bytes(info.extra[offset + 2 : offset + 4], "little")
                offset += 4
                if field_length > len(info.extra) - offset:
                    break
                identifiers.append(field_id)
                offset += field_length
            duplicates = sorted({item for item in identifiers if identifiers.count(item) > 1})
            if duplicates:
                issues.append({"path": info.filename, "duplicate_field_ids": duplicates})
    return issues


def risky_member_permissions(path: Path) -> list[dict[str, object]]:
    """Find Unix members with setuid, setgid, sticky, or world-writable permission bits."""
    risky_bits = (
        (stat.S_ISUID, "setuid"),
        (stat.S_ISGID, "setgid"),
        (stat.S_ISVTX, "sticky"),
        (0o002, "world-writable"),
    )
    results = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            mode = stat.S_IMODE(info.external_attr >> 16)
            flags = [name for bit, name in risky_bits if mode & bit]
            if flags:
                results.append({"path": info.filename, "mode_octal": format(mode, "04o"), "risks": flags})
    return results


def special_file_members(path: Path) -> list[dict[str, str]]:
    """List archive entries marked as Unix devices, FIFOs, or sockets."""
    special_types = {
        stat.S_IFIFO: "fifo",
        stat.S_IFCHR: "character-device",
        stat.S_IFBLK: "block-device",
        stat.S_IFSOCK: "socket",
    }
    results = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            file_type = stat.S_IFMT(info.external_attr >> 16)
            if file_type in special_types:
                results.append({"path": info.filename, "type": special_types[file_type]})
    return results


def _internal_link_target(member: str, target: str) -> Optional[str]:
    """Resolve a relative ZIP symlink target lexically, rejecting rooted escapes."""
    target = target.replace("\\", "/")
    if PurePosixPath(target).is_absolute() or PureWindowsPath(target).drive:
        return None
    parts = member.replace("\\", "/").split("/")[:-1]
    for part in target.split("/"):
        if part in {"", "."}:
            continue
        if part == "..":
            if not parts:
                return None
            parts.pop()
        else:
            parts.append(part)
    return "/".join(parts)


def dangling_symlink_members(path: Path) -> list[dict[str, str]]:
    """Find relative archive symlinks whose normalized target is absent from the ZIP."""
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        names = {info.filename.replace("\\", "/").rstrip("/") for info in entries}
        dangling = []
        for info in entries:
            if not stat.S_ISLNK(info.external_attr >> 16):
                continue
            target = archive.read(info).decode("utf-8", errors="replace")
            resolved = _internal_link_target(info.filename, target)
            if resolved is not None and resolved not in names:
                dangling.append({"path": info.filename, "target": target, "resolved_path": resolved})
        return dangling


def symlink_cycles(path: Path) -> list[list[str]]:
    """Find cycles formed by archive symlinks that point to other symlink members."""
    with zipfile.ZipFile(path) as archive:
        links = {
            info.filename.replace("\\", "/").rstrip("/"): _internal_link_target(
                info.filename, archive.read(info).decode("utf-8", errors="replace")
            )
            for info in archive.infolist()
            if stat.S_ISLNK(info.external_attr >> 16)
        }
    found: set[tuple[str, ...]] = set()
    for start in sorted(links):
        chain: list[str] = []
        positions: dict[str, int] = {}
        current: Optional[str] = start
        while current in links:
            if current in positions:
                cycle = chain[positions[current] :]
                rotations = [tuple(cycle[index:] + cycle[:index]) for index in range(len(cycle))]
                found.add(min(rotations))
                break
            positions[current] = len(chain)
            chain.append(current)
            current = links[current]
    return [list(cycle) for cycle in sorted(found)]


def directory_payload_members(path: Path) -> list[dict[str, object]]:
    """List explicit ZIP directory records that unexpectedly carry payload bytes."""
    with zipfile.ZipFile(path) as archive:
        return [
            {"path": info.filename, "bytes": info.file_size}
            for info in archive.infolist()
            if info.is_dir() and info.file_size > 0
        ]


def implicit_parent_directories(path: Path) -> list[str]:
    """List parent directory paths implied by members but lacking explicit ZIP entries."""
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
    explicit = {info.filename.replace("\\", "/").rstrip("/") for info in entries if info.is_dir()}
    missing = set()
    for info in entries:
        parts = info.filename.replace("\\", "/").strip("/").split("/")[:-1]
        for index in range(1, len(parts) + 1):
            parent = "/".join(parts[:index])
            if parent not in explicit:
                missing.add(parent)
    return sorted(missing)


def future_timestamp_members(path: Path, grace_hours: int = 24) -> list[dict[str, str]]:
    """Find members dated implausibly far in the future, allowing for clock skew."""
    if grace_hours < 0:
        raise ValueError("Timestamp grace period cannot be negative")
    threshold = datetime.now() + timedelta(hours=grace_hours)
    with zipfile.ZipFile(path) as archive:
        return [
            {"path": info.filename, "timestamp": datetime(*info.date_time).isoformat(sep=" ")}
            for info in archive.infolist()
            if datetime(*info.date_time) > threshold
        ]
