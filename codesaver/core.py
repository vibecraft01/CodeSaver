"""Core backup and restore functionality.

Only Python's standard library is used so CodeSaver works on Windows, Linux,
and macOS without extra runtime dependencies.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import os
import tempfile
from typing import Callable, Iterator, Optional, Union
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

from .lang import translate

DEFAULT_EXCLUDED_DIRS = frozenset({".git", "__pycache__", "venv", ".venv", "env", ".env", ".tox", ".mypy_cache"})


class BackupError(RuntimeError):
    """Raised for an expected backup or restore error."""

    def __init__(self, key: str, **values: object) -> None:
        self.key = key
        self.values = values
        super().__init__(translate(key, "en", **values))

    def localized(self, language: str) -> str:
        return translate(self.key, language, **self.values)


class BackupManager:
    """Create and restore project snapshots."""

    def __init__(
        self,
        project_dir: Union[Path, str],
        backup_dir: Optional[Union[Path, str]] = None,
        excluded_dirs: Optional[set[str]] = None,
    ) -> None:
        self.project_dir = Path(project_dir).expanduser().resolve()
        self.backup_dir = (
            Path(backup_dir).expanduser().resolve()
            if backup_dir
            else self.project_dir.parent / f"{self.project_dir.name}-backups"
        )
        self.excluded_dirs = frozenset(excluded_dirs or DEFAULT_EXCLUDED_DIRS)

    def _validate_project(self) -> None:
        if not self.project_dir.exists():
            raise BackupError("errors.project_missing", project=self.project_dir)
        if not self.project_dir.is_dir():
            raise BackupError("errors.project_not_dir", project=self.project_dir)

    def iter_files(self) -> Iterator[Path]:
        """Yield files that belong in a snapshot, in stable order."""
        self._validate_project()
        backup_root = self.backup_dir
        for root, dirs, files in os.walk(self.project_dir, topdown=True, onerror=self._walk_error):
            root_path = Path(root)
            dirs[:] = sorted(
                name for name in dirs if name not in self.excluded_dirs and (root_path / name).resolve() != backup_root
            )
            for name in sorted(files):
                path = root_path / name
                if not path.is_symlink():
                    yield path

    @staticmethod
    def _walk_error(error: OSError) -> None:
        raise error

    def list_files(self) -> list[Path]:
        """Return the files included in the next backup."""
        return list(self.iter_files())

    def create_backup(self, progress_callback: Optional[Callable[[int, int, Path], None]] = None) -> Path:
        """Create a timestamped ZIP archive and return its path.

        The archive is first written to a temporary file in the backup folder,
        then renamed into place so interrupted writes do not look like backups.
        """
        self._validate_project()
        temp_path: Optional[Path] = None
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            files = self.list_files()
            stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            destination = self.backup_dir / f"{self.project_dir.name}_{stamp}.zip"
            fd, temp_name = tempfile.mkstemp(prefix=".codesaver-", suffix=".tmp", dir=self.backup_dir)
            os.close(fd)
            temp_path = Path(temp_name)
            with ZipFile(temp_path, "w", compression=ZIP_DEFLATED) as archive:
                if not files and progress_callback:
                    progress_callback(0, 0, self.project_dir)
                for current, path in enumerate(files, start=1):
                    archive.write(path, path.relative_to(self.project_dir).as_posix())
                    if progress_callback:
                        progress_callback(current, len(files), path)
            temp_path.replace(destination)
            return destination
        except PermissionError as exc:
            if temp_path:
                temp_path.unlink(missing_ok=True)
            raise BackupError("errors.permission", path=getattr(exc, "filename", None) or self.backup_dir) from exc
        except (OSError, ValueError) as exc:
            if temp_path:
                temp_path.unlink(missing_ok=True)
            raise BackupError("errors.create_failed", error=exc) from exc

    def restore_backup(self, archive_path: Union[Path, str], overwrite: bool = False) -> int:
        """Restore an archive into the project directory and return file count.

        Zip member paths are validated to prevent path traversal outside the
        target directory.
        """
        self._validate_project()
        archive = Path(archive_path).expanduser().resolve()
        if not archive.is_file():
            raise BackupError("errors.archive_missing", archive=archive)
        count = 0
        try:
            with ZipFile(archive, "r") as source:
                corrupted_member = source.testzip()
                if corrupted_member:
                    raise BackupError("errors.invalid_zip", archive=archive)
                target_root = self.project_dir.resolve()
                for member in source.infolist():
                    target = (target_root / member.filename).resolve()
                    if target != target_root and target_root not in target.parents:
                        raise BackupError("errors.unsafe_path", member=member.filename)
                    if member.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                        continue
                    if target.exists() and not overwrite:
                        raise BackupError("errors.file_exists", path=target)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with source.open(member) as input_file, target.open("wb") as output_file:
                        output_file.write(input_file.read())
                    count += 1
        except BackupError:
            raise
        except PermissionError as exc:
            raise BackupError("errors.permission", path=getattr(exc, "filename", None) or self.project_dir) from exc
        except (BadZipFile, EOFError, RuntimeError) as exc:
            raise BackupError("errors.invalid_zip", archive=archive) from exc
        except (OSError, ValueError) as exc:
            raise BackupError("errors.restore_failed", error=exc) from exc
        return count
