import json
import tempfile
import unittest
from pathlib import Path

from codesaver.config import load_config
from codesaver.core import BackupError, DEFAULT_EXCLUDED_DIRS


class ConfigTests(unittest.TestCase):
    def test_loads_relative_paths_and_custom_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".codesaver.json"
            config_path.write_text(
                json.dumps(
                    {
                        "interval": 120,
                        "language": "fr-FR",
                        "backup_dir": "backups",
                        "log": "logs/codesaver.log",
                        "excluded_dirs": [".git", "build"],
                    }
                ),
                encoding="utf-8",
            )
            config = load_config(config_path, root)
            self.assertEqual(config.interval, 120)
            self.assertEqual(config.language, "fr")
            self.assertEqual(config.backup_dir, (root / "backups").resolve())
            self.assertEqual(config.log_path, (root / "logs/codesaver.log").resolve())
            self.assertEqual(config.excluded_dirs, frozenset({".git", "build"}))

    def test_missing_optional_config_returns_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = load_config(None, Path(tmp))
            self.assertEqual(config.interval, 600)
            self.assertEqual(config.excluded_dirs, DEFAULT_EXCLUDED_DIRS)

    def test_invalid_config_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaises(BackupError) as context:
                load_config(path, Path(tmp))
            self.assertEqual(context.exception.key, "errors.config_invalid")


if __name__ == "__main__":
    unittest.main()
