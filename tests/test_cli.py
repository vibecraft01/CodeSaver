import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from codesaver.cli import (
    _format_duration,
    _load_recent_projects,
    _progress_callback,
    _remember_project,
    _select_recent_project,
    build_parser,
)


class CliFeatureTests(unittest.TestCase):
    def test_parser_exposes_new_options(self):
        args = build_parser("en").parse_args(
            [
                "--keep-days",
                "30",
                "--follow-symlinks",
                "--dry-run",
                "--verify",
                "--manifest",
                "--exclude-dir",
                "generated",
            ]
        )
        self.assertEqual(args.keep_days, 30)
        self.assertTrue(args.follow_symlinks)
        self.assertTrue(args.dry_run)
        self.assertTrue(args.verify)
        self.assertTrue(args.manifest)
        self.assertEqual(args.exclude_dir, ["generated"])

    def test_eta_is_included_in_progress_output(self):
        output = io.StringIO()
        callback = _progress_callback("en")
        with patch("codesaver.cli.time.monotonic", side_effect=[0.0, 2.0, 4.0]), redirect_stdout(output):
            callback(1, 4, Path("one.py"), 10, 40)
            callback(2, 4, Path("two.py"), 20, 40)
            callback(4, 4, Path("four.py"), 40, 40)
        self.assertIn("ETA: 2s", output.getvalue())
        self.assertIn("ETA: 0s", output.getvalue())
        self.assertEqual(_format_duration(None, "en"), "calculating")

    def test_recent_project_selection_is_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            recent_file = Path(tmp) / "recent.json"
            with patch("codesaver.cli.RECENT_PROJECTS_PATH", recent_file):
                _remember_project(root)
                self.assertEqual(_load_recent_projects(), [root.resolve()])
                output = io.StringIO()
                with patch("builtins.input", return_value="1"), redirect_stdout(output):
                    selected = _select_recent_project("en")
                self.assertEqual(selected, root.resolve())
                self.assertIn(str(root.resolve()), output.getvalue())


if __name__ == "__main__":
    unittest.main()
