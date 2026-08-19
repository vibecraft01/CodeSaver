import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from unittest.mock import patch

from codesaver.core import BackupError, BackupManager


class BackupManagerTests(unittest.TestCase):
    def test_backup_excludes_service_directories_and_can_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            backups = Path(tmp) / "backups"
            root.mkdir()
            (root / "app.py").write_text("print('hello')\n", encoding="utf-8")
            (root / ".git").mkdir()
            (root / ".git" / "config").write_text("secret", encoding="utf-8")
            (root / "__pycache__").mkdir()
            (root / "__pycache__" / "app.pyc").write_bytes(b"ignored")
            archive = BackupManager(root, backups).create_backup()
            with ZipFile(archive) as zip_file:
                self.assertEqual(zip_file.namelist(), ["app.py"])
            (root / "app.py").unlink()
            self.assertEqual(BackupManager(root, backups).restore_backup(archive), 1)
            self.assertEqual((root / "app.py").read_text(encoding="utf-8"), "print('hello')\n")

    def test_custom_exclusions_and_progress_are_applied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            backups = Path(tmp) / "backups"
            root.mkdir()
            (root / "keep.txt").write_text("keep", encoding="utf-8")
            (root / "generated").mkdir()
            (root / "generated" / "ignored.txt").write_text("ignore", encoding="utf-8")
            progress = []
            manager = BackupManager(root, backups, excluded_dirs={"generated"})
            archive = manager.create_backup(lambda current, total, path: progress.append((current, total, path.name)))
            self.assertEqual(progress, [(1, 1, "keep.txt")])
            with ZipFile(archive) as zip_file:
                self.assertEqual(zip_file.namelist(), ["keep.txt"])

    def test_empty_project_reports_zero_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            progress = []
            BackupManager(root).create_backup(lambda current, total, path: progress.append((current, total, path)))
            self.assertEqual(progress[0][0:2], (0, 0))

    def test_restore_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            archive = Path(tmp) / "bad.zip"
            with ZipFile(archive, "w") as zip_file:
                zip_file.writestr("../../outside.txt", "bad")
            with self.assertRaises(BackupError):
                BackupManager(root).restore_backup(archive)

    def test_restore_rejects_damaged_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            archive = Path(tmp) / "damaged.zip"
            archive.write_bytes(b"not a zip archive")
            with self.assertRaises(BackupError) as context:
                BackupManager(root).restore_backup(archive)
            self.assertEqual(context.exception.key, "errors.invalid_zip")

    def test_permission_error_is_reported_as_backup_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            with patch.object(Path, "mkdir", side_effect=PermissionError("denied")):
                with self.assertRaises(BackupError) as context:
                    BackupManager(root, Path(tmp) / "backups").create_backup()
            self.assertEqual(context.exception.key, "errors.permission")


if __name__ == "__main__":
    unittest.main()
