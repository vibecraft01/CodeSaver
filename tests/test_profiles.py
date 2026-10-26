import tempfile
import unittest
import contextlib
import io
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from codesaver.cli import main
from codesaver.profiles import ProfileError, delete_profile, get_profile, list_profiles, save_profile


class ProfileStoreTests(unittest.TestCase):
    def test_profile_round_trip_and_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profiles.json"
            save_profile("Full backup", {"compress": True, "excluded_dirs": [".git", "build"]}, path)
            self.assertEqual(get_profile("Full backup", path)["excluded_dirs"], [".git", "build"])
            save_profile("Full backup", {"compress": False}, path)
            self.assertFalse(get_profile("Full backup", path)["compress"])
            self.assertEqual(
                list_profiles(path),
                {
                    "Full backup": {
                        "compress": False,
                        "excluded_dirs": [],
                        "excluded_extensions": [],
                        "excluded_patterns": [],
                    }
                },
            )

    def test_rejects_invalid_names_and_values_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profiles.json"
            with self.assertRaises(ProfileError):
                save_profile("../escape", {"compress": True}, path)
            with self.assertRaises(ProfileError):
                save_profile("valid", {"keep_last": -1}, path)
            self.assertFalse(path.exists())

    def test_delete_and_missing_profile_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profiles.json"
            save_profile("Temporary", {"compress": True}, path)
            delete_profile("Temporary", path)
            self.assertEqual(list_profiles(path), {})
            with self.assertRaises(ProfileError):
                get_profile("Temporary", path)

    def test_rejects_invalid_profile_data_loaded_from_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profiles.json"
            path.write_text('{"broken": {"keep_last": 0}}', encoding="utf-8")
            with self.assertRaises(ProfileError):
                get_profile("broken", path)

    def test_cli_saves_and_applies_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            (root / "keep.txt").write_text("keep", encoding="utf-8")
            (root / "secret").mkdir()
            (root / "secret" / "private.txt").write_text("private", encoding="utf-8")
            profile_path = Path(tmp) / "profiles.json"
            output = io.StringIO()
            with patch("codesaver.profiles.PROFILES_PATH", profile_path), patch("codesaver.cli._remember_project"):
                with contextlib.redirect_stdout(output):
                    self.assertEqual(
                        main(["--project-dir", str(root), "--exclude-dir", "secret", "--profile-save", "safe"]), 0
                    )
                    self.assertEqual(main(["--profile-list"]), 0)
                    self.assertEqual(
                        main(["--project-dir", str(root), "--profile", "safe", "--backup-now", "--no-autosave"]), 0
                    )
            archives = list((Path(tmp) / "project-backups").glob("*.zip"))
            self.assertEqual(len(archives), 1)
            with ZipFile(archives[0]) as archive:
                self.assertIn("keep.txt", archive.namelist())
                self.assertNotIn("secret/private.txt", archive.namelist())
            self.assertIn("safe", output.getvalue())


if __name__ == "__main__":
    unittest.main()
