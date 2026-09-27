import tempfile
import stat
import unittest
import zipfile
from datetime import date
from pathlib import Path

from codesaver.archive_tools import (
    compare_zips,
    duplicate_contents,
    extract_member,
    find_members,
    member_compression,
    member_permissions,
    members_in_date_range,
    members_larger_than,
    symlink_members,
    verify_zip,
)


class ArchiveToolsTests(unittest.TestCase):
    def test_archive_inspection_and_safe_single_member_extraction(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first.zip"
            second = root / "second.zip"
            with zipfile.ZipFile(first, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("src/main.py", "print('a')\n" * 20)
                archive.writestr("readme.md", "hello")
            with zipfile.ZipFile(second, "w") as archive:
                archive.writestr("src/main.py", "print('b')\n")
                archive.writestr("new.txt", "new")

            self.assertTrue(verify_zip(first)["valid"])
            self.assertEqual(find_members(first, "**/*.PY"), ["src/main.py"])
            report = compare_zips(first, second)
            self.assertEqual(report["added"], ["new.txt"])
            self.assertEqual(report["removed"], ["readme.md"])
            self.assertEqual(report["changed"], ["src/main.py"])
            rows = member_compression(first)
            self.assertEqual(len(rows), 2)
            output = extract_member(first, "src/main.py", root / "out")
            self.assertEqual(output.read_text(encoding="utf-8"), "print('a')\n" * 20)
            with self.assertRaises(FileExistsError):
                extract_member(first, "src/main.py", root / "out")

    def test_single_member_extraction_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive_path = root / "unsafe.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../outside.txt", "no")
            with self.assertRaises(ValueError):
                extract_member(archive_path, "../outside.txt", root / "out")

    def test_archive_metadata_and_content_audits(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive_path = root / "audit.zip"
            link = zipfile.ZipInfo("shortcut")
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            link.date_time = (2026, 9, 27, 10, 0, 0)
            with zipfile.ZipFile(archive_path, "w") as archive:
                old_one = zipfile.ZipInfo("one.txt", (2020, 1, 1, 0, 0, 0))
                old_two = zipfile.ZipInfo("two.txt", (2020, 1, 1, 0, 0, 0))
                old_large = zipfile.ZipInfo("large.bin", (2020, 1, 1, 0, 0, 0))
                archive.writestr(old_one, "same data")
                archive.writestr(old_two, "same data")
                archive.writestr(old_large, "x" * 50)
                archive.writestr(link, "target.txt")

            self.assertEqual(duplicate_contents(archive_path), [["one.txt", "two.txt"]])
            self.assertEqual(symlink_members(archive_path), [{"path": "shortcut", "target": "target.txt"}])
            modes = {item["path"]: item["mode_octal"] for item in member_permissions(archive_path)}
            self.assertEqual(modes["shortcut"], "0777")
            dated = members_in_date_range(archive_path, date(2026, 9, 27), date(2026, 9, 27))
            self.assertEqual({item["path"] for item in dated}, {"shortcut"})
            self.assertEqual(members_larger_than(archive_path, 20), [{"path": "large.bin", "bytes": 50}])


if __name__ == "__main__":
    unittest.main()
