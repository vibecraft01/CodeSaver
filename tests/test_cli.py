import io
import json
import logging
import os
import subprocess
import sys
import stat
import tempfile
import unittest
import warnings
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


def _mark_member_encrypted(path: Path, member_name: str) -> None:
    data = bytearray(path.read_bytes())
    target = member_name.encode("utf-8")
    for signature, name_length_offset, name_start_offset, flag_offset in (
        (b"PK\x03\x04", 26, 30, 6),
        (b"PK\x01\x02", 28, 46, 8),
    ):
        cursor = data.find(signature)
        while cursor >= 0:
            name_length = int.from_bytes(data[cursor + name_length_offset : cursor + name_length_offset + 2], "little")
            name_start = cursor + name_start_offset
            if data[name_start : name_start + name_length] == target:
                flags = int.from_bytes(data[cursor + flag_offset : cursor + flag_offset + 2], "little")
                data[cursor + flag_offset : cursor + flag_offset + 2] = (flags | 1).to_bytes(2, "little")
            cursor = data.find(signature, cursor + len(signature))
    path.write_bytes(data)


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

    def test_archive_metadata_cli_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            backups = Path(tmp) / "backups"
            root.mkdir()
            backups.mkdir()
            archive_path = Path(tmp) / "audit.zip"
            link = zipfile.ZipInfo("shortcut")
            link.create_system = 3
            link.external_attr = (0o120777) << 16
            link.date_time = (2026, 9, 27, 10, 0, 0)
            with zipfile.ZipFile(archive_path, "w") as archive:
                old_one = zipfile.ZipInfo("one.txt", (2020, 1, 1, 0, 0, 0))
                old_two = zipfile.ZipInfo("two.txt", (2020, 1, 1, 0, 0, 0))
                old_large = zipfile.ZipInfo("large.bin", (2020, 1, 1, 0, 0, 0))
                archive.writestr(old_one, "same")
                archive.writestr(old_two, "same")
                archive.writestr(old_large, "x" * 50)
                archive.writestr(link, "target.txt")
            common = [
                "--project-dir",
                str(root),
                "--backup-dir",
                str(backups),
                "--log",
                str(Path(tmp) / "meta.log"),
                "--json",
            ]

            def run(*arguments):
                output = io.StringIO()
                with (
                    patch("codesaver.cli._remember_project"),
                    patch("codesaver.cli.configure_logging", return_value=logging.getLogger("test-archive-metadata")),
                    redirect_stdout(output),
                ):
                    self.assertEqual(main([*common, *arguments]), 0)
                return json.loads(output.getvalue())

            self.assertEqual(
                run("--archive-duplicates", str(archive_path))["duplicate_groups"], [["one.txt", "two.txt"]]
            )
            self.assertEqual(run("--archive-symlinks", str(archive_path))["symlinks"][0]["path"], "shortcut")
            self.assertEqual(run("--archive-permissions", str(archive_path))["members"][-1]["mode_octal"], "0777")
            dated = run("--archive-date-range", str(archive_path), "2026-09-27", "2026-09-27")
            self.assertEqual(dated["members"][0]["path"], "shortcut")
            oversized = run("--archive-larger-than", str(archive_path), "10")
            self.assertEqual(oversized["members"], [{"path": "large.bin", "bytes": 50}])

    def test_archive_security_cli_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            backups = Path(tmp) / "backups"
            root.mkdir()
            backups.mkdir()
            archive_path = Path(tmp) / "security.zip"
            encrypted = zipfile.ZipInfo("secret.bin")
            encrypted.flag_bits |= 0x1
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                    archive.writestr("same.txt", "repeat")
                    archive.writestr("same.txt", "repeat")
                    archive.writestr("Readme.md", "upper")
                    archive.writestr("README.md", "lower")
                    archive.writestr(encrypted, "encrypted")
                    archive.writestr("compressible.txt", "A" * 10000)
            _mark_member_encrypted(archive_path, "secret.bin")
            common = [
                "--project-dir",
                str(root),
                "--backup-dir",
                str(backups),
                "--log",
                str(Path(tmp) / "security.log"),
                "--json",
            ]

            def run(*arguments):
                output = io.StringIO()
                with (
                    patch("codesaver.cli._remember_project"),
                    patch("codesaver.cli.configure_logging", return_value=logging.getLogger("test-archive-security")),
                    redirect_stdout(output),
                ):
                    self.assertEqual(main([*common, *arguments]), 0)
                return json.loads(output.getvalue())

            self.assertEqual(run("--archive-duplicate-paths", str(archive_path))["count"], 1)
            self.assertEqual(
                run("--archive-case-collisions", str(archive_path))["collisions"], [["README.md", "Readme.md"]]
            )
            self.assertEqual(run("--archive-encrypted", str(archive_path))["encrypted_members"], ["secret.bin"])
            methods = run("--archive-methods", str(archive_path))["methods"]
            self.assertEqual({item["method"] for item in methods}, {"stored", "deflate"})
            high_ratio = run("--archive-high-ratio", str(archive_path), "100")
            self.assertEqual(high_ratio["members"][0]["path"], "compressible.txt")

    def test_archive_structure_cli_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            backups = Path(tmp) / "backups"
            root.mkdir()
            backups.mkdir()
            archive_path = Path(tmp) / "structure.zip"
            link = zipfile.ZipInfo("links/outside")
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            executable = zipfile.ZipInfo("bin/tool")
            executable.create_system = 3
            executable.external_attr = (stat.S_IFREG | 0o755) << 16
            file_with_directory_mode = zipfile.ZipInfo("file-with-dir-mode")
            file_with_directory_mode.create_system = 3
            file_with_directory_mode.external_attr = (stat.S_IFDIR | 0o755) << 16
            directory_with_file_mode = zipfile.ZipInfo("dir-with-file-mode/")
            directory_with_file_mode.create_system = 3
            directory_with_file_mode.external_attr = (stat.S_IFREG | 0o644) << 16
            risky_mode = zipfile.ZipInfo("risky.sh")
            risky_mode.create_system = 3
            risky_mode.external_attr = (stat.S_IFREG | stat.S_ISUID | 0o002 | 0o755) << 16
            fifo = zipfile.ZipInfo("pipe")
            fifo.create_system = 3
            fifo.external_attr = (stat.S_IFIFO | 0o600) << 16
            duplicate_extra = zipfile.ZipInfo("extra.bin")
            extra_field = b"\xfe\xca\x01\x00x"
            duplicate_extra.extra = extra_field + extra_field
            long_component = "x" * 256 + ".txt"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("CON.txt", "reserved")
                archive.writestr("café.txt", "composed")
                archive.writestr("cafe\u0301.txt", "decomposed")
                archive.writestr("root", "file")
                archive.writestr("root/child/deep.txt", "nested")
                archive.writestr(link, "../../outside")
                archive.writestr("src/readme.md", "source")
                archive.writestr("docs/readme.md", "docs")
                archive.writestr("config/.env", "secret")
                archive.writestr("win\\legacy.txt", "legacy")
                archive.writestr(executable, "binary")
                archive.writestr("empty/", "")
                archive.writestr("dup/", "")
                archive.writestr("dup/", "")
                archive.writestr(file_with_directory_mode, "data")
                archive.writestr(directory_with_file_mode, "data")
                archive.writestr(long_component, "long")
                archive.writestr("report-\u202eexe.txt", "bidi")
                archive.writestr("unknown.bin", "codec")
                archive.writestr("C:\\drive.txt", "drive")
                archive.writestr("compat/K.txt", "ascii")
                archive.writestr("compat/K.txt", "kelvin")
                archive.writestr(risky_mode, "script")
                archive.writestr(fifo, "")
                archive.writestr(duplicate_extra, "extra")
            zip_bytes = archive_path.read_bytes()
            zip_bytes = bytearray(zip_bytes.replace(b"win/legacy.txt", b"win\\legacy.txt"))
            for signature, name_length_offset, name_start_offset, method_offset in (
                (b"PK\x03\x04", 26, 30, 8),
                (b"PK\x01\x02", 28, 46, 10),
            ):
                cursor = zip_bytes.find(signature)
                while cursor >= 0:
                    name_length = int.from_bytes(
                        zip_bytes[cursor + name_length_offset : cursor + name_length_offset + 2], "little"
                    )
                    name_start = cursor + name_start_offset
                    if zip_bytes[name_start : name_start + name_length] == b"unknown.bin":
                        zip_bytes[cursor + method_offset : cursor + method_offset + 2] = (99).to_bytes(2, "little")
                    cursor = zip_bytes.find(signature, cursor + len(signature))
            archive_path.write_bytes(zip_bytes)
            common = [
                "--project-dir",
                str(root),
                "--backup-dir",
                str(backups),
                "--log",
                str(Path(tmp) / "structure.log"),
                "--json",
            ]

            def run(*arguments):
                output = io.StringIO()
                with (
                    patch("codesaver.cli._remember_project"),
                    patch("codesaver.cli.configure_logging", return_value=logging.getLogger("test-archive-structure")),
                    redirect_stdout(output),
                ):
                    self.assertEqual(main([*common, *arguments]), 0)
                return json.loads(output.getvalue())

            portability = run("--archive-portability-audit", str(archive_path))
            self.assertIn("reserved-device-name", portability["issues"][0]["issues"])
            self.assertEqual(len(run("--archive-unicode-collisions", str(archive_path))["collisions"]), 2)
            depth = run("--archive-depth-report", str(archive_path))
            self.assertEqual(depth["max_depth"], 3)
            self.assertEqual(run("--archive-symlink-audit", str(archive_path))["count"], 1)
            self.assertEqual(run("--archive-prefix-conflicts", str(archive_path))["conflicts"][0]["file"], "root")
            self.assertGreater(run("--archive-path-lengths", str(archive_path))["maximum_characters"], 0)
            self.assertEqual(run("--archive-root-layout", str(archive_path))["root_folders"]["root"], 1)
            self.assertEqual(run("--archive-comments", str(archive_path))["archive_comment"], "")
            self.assertEqual(run("--archive-crc-inventory", str(archive_path))["count"], 21)
            self.assertIn("1980", run("--archive-timestamps", str(archive_path))["files_by_year"])
            self.assertEqual(len(run("--archive-duplicate-basenames", str(archive_path))["groups"]), 2)
            self.assertEqual(run("--archive-hidden-members", str(archive_path))["members"], ["config/.env"])
            self.assertEqual(run("--archive-backslash-paths", str(archive_path))["members"], ["win\\legacy.txt"])
            self.assertEqual(run("--archive-executables", str(archive_path))["members"][0]["path"], "bin/tool")
            self.assertEqual(
                run("--archive-empty-directories", str(archive_path))["directories"],
                ["dir-with-file-mode", "dup", "empty"],
            )
            self.assertEqual(
                run("--archive-unicode-controls", str(archive_path))["members"][0]["characters"][0]["codepoint"],
                "U+202E",
            )
            self.assertEqual(run("--archive-long-components", str(archive_path))["components"][0]["characters"], 260)
            self.assertEqual(run("--archive-duplicate-directories", str(archive_path))["directories"][0]["path"], "dup")
            self.assertEqual(run("--archive-unsupported-compression", str(archive_path))["members"][0]["method_id"], 99)
            self.assertEqual(len(run("--archive-type-conflicts", str(archive_path))["conflicts"]), 2)
            self.assertEqual(run("--archive-absolute-paths", str(archive_path))["members"], ["C:/drive.txt"])
            self.assertEqual(
                run("--archive-unicode-compatibility", str(archive_path))["collisions"],
                [["cafe\u0301.txt", "café.txt"], ["compat/K.txt", "compat/K.txt"]],
            )
            self.assertEqual(
                run("--archive-extra-fields", str(archive_path))["issues"][0]["duplicate_field_ids"], [0xCAFE]
            )
            risky_members = run("--archive-risky-permissions", str(archive_path))["members"]
            self.assertIn("world-writable", risky_members[0]["risks"])
            self.assertEqual(
                run("--archive-special-files", str(archive_path))["members"], [{"path": "pipe", "type": "fifo"}]
            )

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
