import tempfile
import unittest
from pathlib import Path
import os
import time
from zipfile import ZIP_DEFLATED, ZipFile
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

    def test_excluded_extensions_are_not_archived(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            (root / "keep.py").write_text("pass\n", encoding="utf-8")
            (root / "debug.log").write_text("ignore\n", encoding="utf-8")
            archive = BackupManager(root, excluded_extensions={".log"}).create_backup()
            with ZipFile(archive) as zip_file:
                self.assertEqual(zip_file.namelist(), ["keep.py"])

    def test_excluded_glob_patterns_are_not_archived(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            (root / "keep.py").write_text("pass\n", encoding="utf-8")
            (root / "debug.tmp").write_text("ignore\n", encoding="utf-8")
            (root / "temp_generated.txt").write_text("ignore\n", encoding="utf-8")
            archive = BackupManager(root, excluded_patterns={"*.tmp", "temp_*"}).create_backup()
            with ZipFile(archive) as zip_file:
                self.assertEqual(zip_file.namelist(), ["keep.py"])

    def test_keep_days_removes_aged_backups(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            backups = Path(tmp) / "backups"
            root.mkdir()
            backups.mkdir()
            old_archive = backups / "project_old.zip"
            old_archive.write_bytes(b"old")
            os.utime(old_archive, (time.time() - 3 * 86400, time.time() - 3 * 86400))
            (root / "app.py").write_text("pass\n", encoding="utf-8")
            manager = BackupManager(root, backups, keep_days=1)
            manager.create_backup()
            self.assertFalse(old_archive.exists())
            self.assertEqual(manager.last_cleanup_count, 1)

    def test_follow_symlinks_archives_target_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            target = Path(tmp) / "target.txt"
            root.mkdir()
            target.write_bytes(b"linked content\n")
            link = root / "linked.txt"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symbolic links are unavailable: {exc}")
            archive = BackupManager(root, follow_symlinks=True).create_backup()
            with ZipFile(archive) as zip_file:
                self.assertEqual(zip_file.read("linked.txt"), b"linked content\n")

    def test_unreadable_file_is_skipped_and_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            (root / "keep.py").write_text("pass\n", encoding="utf-8")
            skipped = root / "skip.py"
            skipped.write_text("skip\n", encoding="utf-8")
            errors = []
            original_write = ZipFile.write

            def write_file(archive, filename, *args, **kwargs):
                if Path(filename).name == "skip.py":
                    raise PermissionError("denied")
                return original_write(archive, filename, *args, **kwargs)

            with patch.object(ZipFile, "write", write_file):
                archive = BackupManager(
                    root, file_error_callback=lambda path, error: errors.append((path, error))
                ).create_backup()
            with ZipFile(archive) as zip_file:
                self.assertEqual(zip_file.namelist(), ["keep.py"])
            self.assertEqual(errors[0][0], skipped)

    def test_compression_max_size_and_detailed_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            backups = Path(tmp) / "backups"
            root.mkdir()
            (root / "small.txt").write_bytes(b"1234")
            (root / "large.bin").write_bytes(b"1234567890")
            progress = []
            manager = BackupManager(root, backups, compress=True, max_size=4)
            archive = manager.create_backup(detailed_progress_callback=lambda *values: progress.append(values))
            self.assertEqual(progress[0][0:2], (1, 1))
            self.assertEqual(progress[0][3:], (4, 4))
            with ZipFile(archive) as zip_file:
                self.assertEqual(zip_file.namelist(), ["small.txt"])
                self.assertEqual(zip_file.getinfo("small.txt").compress_type, ZIP_DEFLATED)

    def test_gitignore_rules_are_applied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            (root / ".gitignore").write_text("*.log\nignored_dir/\n!ignored_dir/keep.txt\n", encoding="utf-8")
            (root / "app.py").write_text("pass\n", encoding="utf-8")
            (root / "debug.log").write_text("ignore\n", encoding="utf-8")
            ignored_dir = root / "ignored_dir"
            ignored_dir.mkdir()
            (ignored_dir / "drop.txt").write_text("ignore\n", encoding="utf-8")
            (ignored_dir / "keep.txt").write_text("keep\n", encoding="utf-8")
            archive = BackupManager(root).create_backup()
            with ZipFile(archive) as zip_file:
                self.assertEqual(set(zip_file.namelist()), {".gitignore", "app.py", "ignored_dir/keep.txt"})

    def test_keep_last_removes_old_project_backups(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            backups = Path(tmp) / "backups"
            root.mkdir()
            backups.mkdir()
            for index in range(3):
                path = backups / f"project_old_{index}.zip"
                path.write_bytes(b"old")
                old_time = time.time() - (100 - index)
                os.utime(path, (old_time, old_time))
            manager = BackupManager(root, backups, keep_last=2)
            manager.create_backup()
            archives = sorted(backups.glob("project_*.zip"))
            self.assertEqual(len(archives), 2)

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
