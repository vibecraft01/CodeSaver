import io
import json
import logging
import subprocess
import sys
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
    _write_backup_report,
    _health_check,
    _backup_stats,
)
from codesaver.core import BackupManager


class CliFeatureTests(unittest.TestCase):
    def test_module_entrypoint_returns_nonzero_for_invalid_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "broken.zip"
            archive.write_bytes(b"not a ZIP archive")
            result = subprocess.run(
                [sys.executable, "-m", "codesaver", "--language", "en", "--project-dir", tmp, "--diff", archive],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("damaged", result.stdout)

    def test_parser_exposes_new_options(self):
        args = build_parser("en").parse_args(
            [
                "--keep-days",
                "30",
                "--follow-symlinks",
                "--dry-run",
                "--git-context",
                "--restore-files",
                "backup.zip",
                "src/app.py",
                "--verify",
                "--manifest",
                "--list",
                "backup.zip",
                "--exclude-pattern",
                "*.tmp",
                "--exclude-dir",
                "generated",
                "--report",
                "report.json",
            ]
        )
        self.assertEqual(args.keep_days, 30)
        self.assertTrue(args.follow_symlinks)
        self.assertTrue(args.dry_run)
        self.assertTrue(args.git_context)
        self.assertEqual(args.restore_files, ["backup.zip", "src/app.py"])
        self.assertTrue(args.verify)
        self.assertTrue(args.manifest)
        self.assertEqual(args.list, Path("backup.zip"))
        self.assertEqual(args.exclude_pattern, ["*.tmp"])
        self.assertEqual(args.exclude_dir, ["generated"])
        self.assertEqual(args.report, Path("report.json"))

    def test_health_check_reports_corrupt_archives(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            backups = Path(tmp) / "backups"
            root.mkdir()
            root.joinpath("hello.py").write_text("print('ok')", encoding="utf-8")
            manager = BackupManager(root, backups)
            manager.create_backup()
            broken = backups / "project_broken.zip"
            broken.write_bytes(b"not a zip")
            total, failed = _health_check(manager, logging.getLogger("test-health"))
            self.assertEqual(total, 2)
            self.assertEqual([path.resolve() for path in failed], [broken.resolve()])

    def test_backup_stats_reports_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            backups = Path(tmp) / "backups"
            root.mkdir()
            root.joinpath("hello.py").write_text("print('ok')", encoding="utf-8")
            manager = BackupManager(root, backups)
            archive = manager.create_backup()
            stats = _backup_stats(manager)
            self.assertEqual(stats["count"], 1)
            self.assertEqual(stats["total_bytes"], archive.stat().st_size)
            self.assertEqual(stats["newest"], str(archive))
            self.assertEqual(stats["oldest"], str(archive))

    def test_backup_report_contains_audit_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            backups = Path(tmp) / "backups"
            root.mkdir()
            (root / "hello.py").write_text("print('ok')", encoding="utf-8")
            manager = BackupManager(root, backups)
            archive = manager.create_backup()
            report_path = Path(tmp) / "reports" / "backup.json"
            report = _write_backup_report(report_path, manager, archive, 1.25, True, False)
            self.assertTrue(report_path.is_file())
            self.assertEqual(report["files"], 1)
            self.assertEqual(report["verified"], True)
            self.assertEqual(json.loads(report_path.read_text(encoding="utf-8"))["archive"], str(archive))

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
