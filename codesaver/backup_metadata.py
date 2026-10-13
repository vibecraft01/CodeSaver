"""Persistent labels and notes for local backup archives."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Optional, Union


class BackupMetadataStore:
    """Store annotations in a small index beside the backup archives."""

    def __init__(self, backup_dir: Union[Path, str]) -> None:
        self.backup_dir = Path(backup_dir).expanduser().resolve()
        self.index_path = self.backup_dir / ".codesaver-metadata.json"

    def _load(self) -> dict[str, dict[str, str]]:
        if not self.index_path.exists():
            return {}
        payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("schema") != 1 or not isinstance(payload.get("archives"), dict):
            raise ValueError(f"Invalid CodeSaver metadata index: {self.index_path}")
        result: dict[str, dict[str, str]] = {}
        for name, item in payload["archives"].items():
            if isinstance(name, str) and isinstance(item, dict):
                values = {key: item.get(key, "") for key in ("label", "note")}
                if not all(isinstance(value, str) for value in values.values()):
                    raise ValueError(f"Invalid annotation in CodeSaver metadata index: {name}")
                result[name] = values
        return result

    def _save(self, records: dict[str, dict[str, str]]) -> None:
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        payload = {"schema": 1, "archives": records}
        descriptor, temporary = tempfile.mkstemp(prefix=".codesaver-metadata-", suffix=".tmp", dir=self.backup_dir)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(payload, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            os.replace(temporary, self.index_path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _archive_name(self, archive: Union[Path, str]) -> str:
        candidate = Path(archive).expanduser()
        if not candidate.is_absolute():
            candidate = self.backup_dir / candidate
        candidate = candidate.resolve()
        if candidate.parent != self.backup_dir or candidate.suffix.lower() != ".zip" or not candidate.is_file():
            raise ValueError(f"Archive must be an existing ZIP directly inside {self.backup_dir}: {archive}")
        return candidate.name

    def get(self, archive: Union[Path, str]) -> dict[str, str]:
        name = self._archive_name(archive)
        return self._load().get(name, {"label": "", "note": ""})

    def update(
        self,
        archive: Union[Path, str],
        *,
        label: Optional[str] = None,
        note: Optional[str] = None,
    ) -> dict[str, str]:
        name = self._archive_name(archive)
        if label is None and note is None:
            raise ValueError("Provide a label, a note, or both")
        records = self._load()
        current = records.setdefault(name, {"label": "", "note": ""})
        if label is not None:
            current["label"] = label.strip()
        if note is not None:
            current["note"] = note.strip()
        if not current["label"] and not current["note"]:
            records.pop(name)
        self._save(records)
        return current

    def catalog(self, query: str = "") -> list[dict[str, Any]]:
        records = self._load()
        needle = query.strip().casefold()
        rows = []
        if not self.backup_dir.exists():
            return rows
        for archive in sorted(self.backup_dir.glob("*.zip"), key=lambda item: item.name.casefold()):
            if not archive.is_file():
                continue
            annotation = records.get(archive.name, {"label": "", "note": ""})
            if needle and needle not in " ".join((archive.name, annotation["label"], annotation["note"])).casefold():
                continue
            rows.append(
                {
                    "archive": archive.name,
                    "path": str(archive.resolve()),
                    "bytes": archive.stat().st_size,
                    "label": annotation["label"],
                    "note": annotation["note"],
                }
            )
        return rows

    def rename_entry(self, old_name: str, new_archive: Union[Path, str]) -> None:
        new_name = self._archive_name(new_archive)
        old_path = (self.backup_dir / old_name).resolve()
        if old_path.parent != self.backup_dir or old_path.suffix.lower() != ".zip" or old_path.exists():
            raise ValueError(f"Invalid previous archive name: {old_name}")
        records = self._load()
        if old_name in records:
            records[new_name] = records.pop(old_name)
            self._save(records)

    def discard_entry(self, archive_name: str) -> None:
        path = (self.backup_dir / archive_name).resolve()
        if path.parent != self.backup_dir or path.suffix.lower() != ".zip":
            raise ValueError(f"Invalid archive name: {archive_name}")
        records = self._load()
        if records.pop(archive_name, None) is not None:
            self._save(records)

    def export(self, destination: Union[Path, str]) -> int:
        target = Path(destination).expanduser()
        resolved_target = target.resolve()
        if resolved_target == self.index_path or resolved_target.suffix.casefold() == ".zip":
            raise ValueError("Catalog export cannot overwrite the metadata index or a ZIP archive")
        target.parent.mkdir(parents=True, exist_ok=True)
        rows = self.catalog()
        if target.suffix.casefold() == ".csv":
            with target.open("w", newline="", encoding="utf-8-sig") as stream:
                writer = csv.DictWriter(stream, fieldnames=("archive", "path", "bytes", "label", "note"))
                writer.writeheader()
                writer.writerows(rows)
        else:
            target.write_text(json.dumps({"archives": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return len(rows)
