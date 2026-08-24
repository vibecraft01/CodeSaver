import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch
from zipfile import ZipFile

from desktop.backup_manager import DesktopBackupManager
from desktop.utils import (
    DesktopSettings,
    archive_details,
    backup_summary,
    detect_system_theme,
    detect_system_language,
    format_bytes,
    load_settings,
    save_settings,
    theme_colors,
)


class DesktopSupportTests(unittest.TestCase):
    def test_system_theme_detection_and_default(self):
        self.assertEqual(DesktopSettings().theme, "system")

        class FakeWinreg:
            HKEY_CURRENT_USER = object()

            class Key:
                def __enter__(self):
                    return self

                def __exit__(self, *_args):
                    return None

            @staticmethod
            def OpenKey(_root, _path):
                return FakeWinreg.Key()

            @staticmethod
            def QueryValueEx(_key, _name):
                return 1, None

        with (
            patch("desktop.utils.os.name", "nt"),
            patch("desktop.utils.sys.platform", "win32"),
            patch.dict(sys.modules, {"winreg": FakeWinreg}),
        ):
            self.assertEqual(detect_system_theme(), "light")

    def test_settings_round_trip_and_formatting(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "desktop.json"
            settings = DesktopSettings(
                project_dir=str(Path(tmp) / "project"),
                backup_dir=str(Path(tmp) / "backups"),
                excluded_extensions=(".log",),
                interval_minutes=5,
                keep_last=3,
                theme="light",
                accent_color="#FF8800",
                compress=False,
                language="auto",
                backup_on_start=True,
                recent_projects=(str(Path(tmp) / "project"),),
            )
            save_settings(settings, config_path)
            loaded = load_settings(config_path)
            self.assertEqual(Path(loaded.project_dir), Path(settings.project_dir).resolve())
            self.assertEqual(loaded.excluded_extensions, settings.excluded_extensions)
            self.assertEqual(loaded.keep_last, 3)
            self.assertEqual(loaded.theme, "light")
            self.assertEqual(loaded.accent_color, "#FF8800")
            self.assertTrue(loaded.backup_on_start)
            self.assertTrue(loaded.verify_after_backup)
            self.assertEqual(loaded.recent_projects, (str(Path(tmp) / "project"),))
            self.assertEqual(format_bytes(1024 * 1024), "1.0 MB")

    def test_custom_theme_palette_and_language_detection(self):
        palette = theme_colors("ocean", "#AA33CC")
        self.assertEqual(palette["background"], "#071A26")
        self.assertEqual(palette["accent"], "#AA33CC")
        with patch.dict("os.environ", {"LC_ALL": "ru_RU.UTF-8", "LANG": ""}, clear=False):
            self.assertEqual(detect_system_language(), "ru")

    def test_recent_projects_are_limited_to_five(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            projects = []
            for index in range(6):
                project = root / f"project-{index}"
                project.mkdir()
                projects.append(str(project))
            settings = DesktopSettings(recent_projects=tuple(projects))
            self.assertEqual(len(settings.recent_projects), 6)
            config_path = root / "desktop.json"
            save_settings(settings, config_path)
            loaded = load_settings(config_path)
            self.assertEqual(len(loaded.recent_projects), 5)
            self.assertEqual(loaded.recent_projects[0], str(Path(projects[0]).resolve()))

    def test_desktop_manager_creates_archive_and_lists_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            backups = Path(tmp) / "backups"
            root.mkdir()
            (root / "app.py").write_text("pass\n", encoding="utf-8")
            settings = DesktopSettings(backup_dir=str(backups), language="en")
            manager = DesktopBackupManager(root, settings)
            archive = manager.create_backup()
            self.assertEqual(archive_details(backups)[0][0], archive.resolve())
            (root / "app.py").unlink()
            self.assertEqual(manager.restore_backup(archive), 1)
            with ZipFile(archive) as zip_file:
                self.assertEqual(zip_file.namelist(), ["app.py"])

    def test_desktop_manager_verifies_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            (root / "app.py").write_text("pass\n", encoding="utf-8")
            manager = DesktopBackupManager(root, DesktopSettings(backup_dir=str(Path(tmp) / "backups")))
            archive = manager.create_backup()
            self.assertEqual(manager.verify_backup(archive), 1)

    def test_desktop_manager_compares_archive_with_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            (root / "app.py").write_text("old\n", encoding="utf-8")
            manager = DesktopBackupManager(root, DesktopSettings(backup_dir=str(Path(tmp) / "backups")))
            archive = manager.create_backup()
            (root / "app.py").write_text("new\n", encoding="utf-8")
            (root / "added.txt").write_text("added\n", encoding="utf-8")
            diff = manager.compare_backup(archive)
            self.assertEqual(diff["added"], ["added.txt"])
            self.assertEqual(diff["modified"], ["app.py"])
            self.assertEqual(diff["missing"], [])

    def test_cleanup_old_backups_uses_keep_last(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            backups = Path(tmp) / "backups"
            root.mkdir()
            (root / "app.py").write_text("pass\n", encoding="utf-8")
            settings = DesktopSettings(backup_dir=str(backups), keep_last=0)
            manager = DesktopBackupManager(root, settings)
            first = manager.create_backup()
            first.rename(backups / "project_old.zip")
            manager.create_backup()
            manager.core.keep_last = 1
            self.assertEqual(manager.cleanup_old_backups(), 1)
            self.assertEqual(len(list(backups.glob("*.zip"))), 1)

    def test_backup_summary_reports_archive_count_and_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            backups = Path(tmp) / "backups"
            root.mkdir()
            manager = DesktopBackupManager(root, DesktopSettings(backup_dir=str(backups)))
            first = manager.create_backup()
            first = first.rename(backups / "first.zip")
            second = manager.create_backup()
            count, size = backup_summary(backups)
            self.assertEqual(count, 2)
            self.assertEqual(size, first.stat().st_size + second.stat().st_size)


if __name__ == "__main__":
    unittest.main()
