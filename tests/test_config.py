import json
import tempfile
import unittest
from pathlib import Path

from codesaver.config import load_config, parse_size
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
                        "exclude_ext": ["tmp", ".LOG"],
                        "compress": True,
                        "max_size": "100M",
                        "keep_last": 3,
                        "use_gitignore": False,
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
            self.assertEqual(config.excluded_extensions, frozenset({".tmp", ".log"}))
            self.assertTrue(config.compress)
            self.assertEqual(config.max_size, 100_000_000)
            self.assertEqual(config.keep_last, 3)
            self.assertFalse(config.use_gitignore)

    def test_parse_size_accepts_common_units(self):
        self.assertEqual(parse_size("100M"), 100_000_000)
        self.assertEqual(parse_size("1MiB"), 1024 * 1024)
        self.assertEqual(parse_size(42), 42)

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
