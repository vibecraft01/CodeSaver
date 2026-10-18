"""Compare consecutive backup snapshots and summarize project evolution."""

from __future__ import annotations

import csv
import hashlib
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any


def _member_digest(archive: zipfile.ZipFile, member: zipfile.ZipInfo) -> str:
    digest = hashlib.sha256()
    with archive.open(member) as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def backup_evolution(backup_dir: Path, path_filter: str = "") -> dict[str, Any]:
    """Return per-file changes between consecutive ZIP snapshots.

    The optional path filter is applied to member names before each transition
    is summarized, making the report useful for large projects and CI checks.
    """
    archives = sorted(
        (path for path in backup_dir.glob("*.zip") if path.is_file()),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
    )
    needle = path_filter.casefold().strip()
    inventories: list[tuple[Path, dict[str, tuple[int, str]]]] = []
    for archive in archives:
        with zipfile.ZipFile(archive) as bundle:
            inventory = {
                item.filename: (item.file_size, _member_digest(bundle, item))
                for item in bundle.infolist()
                if not item.is_dir() and (not needle or needle in item.filename.casefold())
            }
        inventories.append((archive, inventory))

    transitions = []
    for (older, before), (newer, after) in zip(inventories, inventories[1:]):
        changes = []
        for name in sorted(after.keys() - before.keys()):
            changes.append({"path": name, "status": "added", "before_bytes": 0, "after_bytes": after[name][0]})
        for name in sorted(before.keys() - after.keys()):
            changes.append({"path": name, "status": "removed", "before_bytes": before[name][0], "after_bytes": 0})
        for name in sorted(before.keys() & after.keys()):
            if before[name][1] != after[name][1]:
                changes.append(
                    {
                        "path": name,
                        "status": "modified",
                        "before_bytes": before[name][0],
                        "after_bytes": after[name][0],
                    }
                )
        transitions.append(
            {
                "from_archive": older.name,
                "to_archive": newer.name,
                "from_created": datetime.fromtimestamp(older.stat().st_mtime).astimezone().isoformat(),
                "to_created": datetime.fromtimestamp(newer.stat().st_mtime).astimezone().isoformat(),
                "added": sum(change["status"] == "added" for change in changes),
                "modified": sum(change["status"] == "modified" for change in changes),
                "removed": sum(change["status"] == "removed" for change in changes),
                "net_bytes": sum(change["after_bytes"] - change["before_bytes"] for change in changes),
                "changes": changes,
            }
        )
    return {
        "operation": "backup-evolution",
        "snapshots": len(archives),
        "transitions": transitions,
        "change_count": sum(len(item["changes"]) for item in transitions),
    }


def export_evolution_csv(report: dict[str, Any], destination: Path) -> None:
    """Export one row per changed project path across all transitions."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    fields = (
        "from_archive",
        "to_archive",
        "from_created",
        "to_created",
        "status",
        "path",
        "before_bytes",
        "after_bytes",
    )
    with destination.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for transition in report["transitions"]:
            for change in transition["changes"]:
                writer.writerow(
                    {
                        "from_archive": transition["from_archive"],
                        "to_archive": transition["to_archive"],
                        "from_created": transition["from_created"],
                        "to_created": transition["to_created"],
                        **change,
                    }
                )


def evolution_has_changes(report: dict[str, Any]) -> bool:
    """Whether any transition contains at least one changed project member."""
    return bool(report["change_count"])
