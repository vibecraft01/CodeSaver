"""CodeSaver: automatic ZIP backups for source code projects."""

from .core import BackupManager, BackupError

__all__ = ["BackupError", "BackupManager"]
__version__ = "1.2.9"
