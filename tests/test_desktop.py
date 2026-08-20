import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from desktop.backup_manager import DesktopBackupManager
from desktop.utils import DesktopSettings, archive_details, format_bytes, load_settings, save_settings


class DesktopSupportTests(unittest.TestCase):
    def test_settings_round_trip_and_formatting(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "desktop.json"
            settings = DesktopSettings(
                project_dir=str(Path(tmp) / "project"),
                backup_dir=str(Path(tmp) / "backups"),
                excluded_extensions=(".log",),
                interval_minutes=5,
                keep_last=3,
                language="en",
                theme="light",
                compress=False,
            )
            save_settings(settings, config_path)
            loaded = load_settings(config_path)
            self.assertEqual(loaded.project_dir, settings.project_dir)
            self.assertEqual(loaded.excluded_extensions, settings.excluded_extensions)
            self.assertEqual(loaded.keep_last, 3)
            self.assertEqual(loaded.theme, "light")
            self.assertEqual(format_bytes(1024 * 1024), "1.0 MB")

    def test_desktop_manager_creates_archive_and_lists_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            backups = Path(tmp) / "backups"
            root.mkdir()
            (root / "app.py").write_text("pass\n", encoding="utf-8")
            settings = DesktopSettings(backup_dir=str(backups), language="en")
            manager = DesktopBackupManager(root, settings)
            archive = manager.create_backup()
            self.assertEqual(archive_details(backups)[0][0], archive)
            (root / "app.py").unlink()
            self.assertEqual(manager.restore_backup(archive), 1)
            with ZipFile(archive) as zip_file:
                self.assertEqual(zip_file.namelist(), ["app.py"])


if __name__ == "__main__":
    unittest.main()
