"""GUI adapter around CodeSaver's tested core backup manager."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional, Union

from codesaver.core import BackupManager

from .utils import DesktopSettings


class DesktopBackupManager:
    """Expose the core manager with settings suitable for the desktop UI."""

    def __init__(self, project_dir: Union[Path, str], settings: DesktopSettings) -> None:
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
        )

    @property
    def project_dir(self) -> Path:
        return self.core.project_dir

    @property
    def backup_dir(self) -> Path:
        return self.core.backup_dir

    def list_files(self) -> list[Path]:
        return self.core.list_files()

    def create_backup(self, progress_callback: Optional[Callable[..., None]] = None) -> Path:
        return self.core.create_backup(detailed_progress_callback=progress_callback)

    def restore_backup(self, archive_path: Union[Path, str], overwrite: bool = False) -> int:
        return self.core.restore_backup(archive_path, overwrite=overwrite)
