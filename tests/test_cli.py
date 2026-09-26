import io
import json
import logging
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
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
    _self_check,
    main,
)
from codesaver.core import BackupManager


class CliFeatureTests(unittest.TestCase):
    def test_new_archive_commands_are_reachable_from_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            backups = Path(tmp) / "backups"
            root.mkdir()
            backups.mkdir()
            first = Path(tmp) / "first.zip"
            second = Path(tmp) / "second.zip"
            with zipfile.ZipFile(first, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("src/app.py", "print('first')\n" * 10)
            with zipfile.ZipFile(second, "w") as archive:
                archive.writestr("src/app.py", "print('second')\n")
                archive.writestr("new.txt", "new")
            common = [
                "--project-dir",
                str(root),
                "--backup-dir",
                str(backups),
                "--log",
                str(Path(tmp) / "run.log"),
                "--json",
            ]

            def run(*arguments):
                output = io.StringIO()
                with (
                    patch("codesaver.cli._remember_project"),
                    patch("codesaver.cli.configure_logging", return_value=logging.getLogger("test-archive-commands")),
                    redirect_stdout(output),
                ):
                    self.assertEqual(main([*common, *arguments]), 0)
                return json.loads(output.getvalue())

            self.assertTrue(run("--archive-verify-crc", str(first))["valid"])
            self.assertEqual(
                run("--archive-find-members", str(first), "--member-glob", "**/*.PY")["matches"], ["src/app.py"]
            )
            compared = run("--compare-zips", str(first), str(second))
            self.assertEqual(compared["added"], ["new.txt"])
            self.assertEqual(compared["changed"], ["src/app.py"])
            extracted = run(
                "--archive-extract-member", str(first), "src/app.py", "--extract-to", str(Path(tmp) / "out")
            )
            self.assertTrue(Path(extracted["output"]).is_file())
            compression = run("--member-compression", str(first))
            self.assertEqual(compression["members"][0]["path"], "src/app.py")

    def test_safety_and_maintenance_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            backups = Path(tmp) / "backups"
            root.mkdir()
            backups.mkdir()
            (root / "replace.txt").write_text("current", encoding="utf-8")
            long_dir = root / "directory-name-longer-than-limit"
            long_dir.mkdir()
            (long_dir / "file.txt").write_text("content", encoding="utf-8")
            archive_path = Path(tmp) / "sample.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("replace.txt", "saved")
                archive.writestr("../outside.txt", "unsafe")
                archive.writestr("C:\\outside.txt", "unsafe")
            old_backup = backups / "old.zip"
            with zipfile.ZipFile(old_backup, "w"):
                pass
            old_time = 1
            os.utime(old_backup, (old_time, old_time))
            common = [
                "--project-dir",
                str(root),
                "--backup-dir",
                str(backups),
                "--log",
                str(Path(tmp) / "run.log"),
                "--json",
            ]

            outputs = {}
            for option, value in (
                ("--restore-conflicts", str(archive_path)),
                ("--archive-path-audit", str(archive_path)),
                ("--project-long-paths", "10"),
                ("--backup-age-over-limit", "1"),
            ):
                output = io.StringIO()
                with patch("codesaver.cli._remember_project"):
                    with patch(
                        "codesaver.cli.configure_logging", return_value=logging.getLogger("test-cli-new-reports")
                    ):
                        with redirect_stdout(output):
                            self.assertEqual(main([*common, option, value]), 0)
                outputs[option] = json.loads(output.getvalue())

            self.assertEqual(outputs["--restore-conflicts"]["conflicts"], ["replace.txt"])
            unsafe_members = [member.replace("\\", "/") for member in outputs["--archive-path-audit"]["unsafe_members"]]
            self.assertCountEqual(unsafe_members, ["../outside.txt", "C:/outside.txt"])
            self.assertGreater(outputs["--project-long-paths"]["count"], 0)
            self.assertEqual(outputs["--backup-age-over-limit"]["count"], 1)

            corrupt_archive = Path(tmp) / "corrupt.zip"
            corrupt_archive.write_text("not a zip", encoding="utf-8")
            with patch("codesaver.cli._remember_project"):
                with patch("codesaver.cli.configure_logging", return_value=logging.getLogger("test-cli-new-reports")):
                    with redirect_stdout(io.StringIO()):
                        self.assertEqual(main([*common, "--archive-path-audit", str(corrupt_archive)]), 1)

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
                "--checksum",
                "backup.zip",
                "--doctor",
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
        self.assertEqual(args.checksum, Path("backup.zip"))
        self.assertTrue(args.doctor)
        self.assertEqual(args.restore_files, ["backup.zip", "src/app.py"])
        self.assertTrue(args.verify)
        self.assertTrue(args.manifest)
        self.assertEqual(args.list, Path("backup.zip"))
        self.assertEqual(args.exclude_pattern, ["*.tmp"])
        self.assertEqual(args.exclude_dir, ["generated"])
        self.assertEqual(args.report, Path("report.json"))

    def test_self_check_runs_disposable_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            root.joinpath("hello.py").write_text("print('ok')", encoding="utf-8")
            result = _self_check(BackupManager(root, Path(tmp) / "backups"))
            self.assertTrue(result["test_backup"])
            self.assertTrue(result["project_readable"])
            self.assertTrue(result["ok"])

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
