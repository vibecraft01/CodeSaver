import tempfile
import stat
import unittest
import zipfile
from datetime import date
import warnings
from pathlib import Path

from codesaver.archive_tools import (
    compare_zips,
    case_colliding_paths,
    compression_methods,
    duplicate_contents,
    duplicate_member_paths,
    encrypted_members,
    extract_member,
    find_members,
    high_ratio_members,
    member_compression,
    member_permissions,
    members_in_date_range,
    members_larger_than,
    symlink_members,
    verify_zip,
)


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

    def test_archive_security_and_portability_audits(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive_path = Path(temporary) / "security.zip"
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

            duplicates = duplicate_member_paths(archive_path)
            self.assertEqual(duplicates, [{"path": "same.txt", "entries": [0, 1]}])
            self.assertEqual(case_colliding_paths(archive_path), [["README.md", "Readme.md"]])
            self.assertEqual(encrypted_members(archive_path), ["secret.bin"])
            methods = compression_methods(archive_path)
            self.assertEqual({item["method"] for item in methods}, {"stored", "deflate"})
            self.assertEqual(sum(int(item["files"]) for item in methods), 6)
            ratios = high_ratio_members(archive_path, 100)
            self.assertEqual([item["path"] for item in ratios], ["compressible.txt"])


if __name__ == "__main__":
    unittest.main()
