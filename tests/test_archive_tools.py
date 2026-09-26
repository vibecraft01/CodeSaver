import tempfile
import unittest
import zipfile
from pathlib import Path

from codesaver.archive_tools import compare_zips, extract_member, find_members, member_compression, verify_zip


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


if __name__ == "__main__":
    unittest.main()
