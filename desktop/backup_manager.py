"""GUI adapter around CodeSaver's tested core backup manager."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional, Union

from codesaver.core import BackupManager

from .utils import DesktopSettings


class DesktopBackupManager:
    """Expose the core manager with settings suitable for the desktop UI."""

    def __init__(self, project_dir: Union[Path, str], settings: DesktopSettings) -> None:
        self.last_errors: list[tuple[Path, BaseException]] = []
        self.verify_after_backup = settings.verify_after_backup
        backup_dir = settings.backup_dir or str(Path(project_dir).parent / f"{Path(project_dir).name}-backups")
        self.core = BackupManager(
            project_dir,
            backup_dir,
            excluded_dirs=set(settings.excluded_dirs),
            excluded_extensions=set(settings.excluded_extensions),
            compress=settings.compress,
            max_size=settings.max_size,
            keep_last=settings.keep_last or None,
            use_gitignore=True,
            file_error_callback=self._record_file_error,
        )

    def _record_file_error(self, path: Path, error: BaseException) -> None:
        self.last_errors.append((path, error))

    @property
    def project_dir(self) -> Path:
        return self.core.project_dir

    @property
    def backup_dir(self) -> Path:
        return self.core.backup_dir

    def list_files(self) -> list[Path]:
        return self.core.list_files()

    def create_backup(self, progress_callback: Optional[Callable[..., None]] = None) -> Path:
        self.last_errors.clear()
        return self.core.create_backup(detailed_progress_callback=progress_callback)

    def restore_backup(self, archive_path: Union[Path, str], overwrite: bool = False) -> int:
        return self.core.restore_backup(archive_path, overwrite=overwrite)

    def restore_files(self, archive_path: Union[Path, str], members: list[str], overwrite: bool = False) -> int:
        return self.core.restore_files(archive_path, members, overwrite=overwrite)

    def verify_backup(self, archive_path: Union[Path, str]) -> int:
        """Validate ZIP CRCs and any embedded SHA-256 manifest."""
        return self.core.verify_backup(archive_path)

    def compare_backup(self, archive_path: Union[Path, str]) -> dict[str, list[str]]:
        """Compare the current project with an archive for a restore preview."""
        return self.core.compare_backup(archive_path)

    def cleanup_old_backups(self) -> int:
        return self.core.cleanup_old_backups()
