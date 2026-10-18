import csv
import tempfile
import unittest
import zipfile
from pathlib import Path

from codesaver.evolution import backup_evolution, evolution_has_changes, export_evolution_csv


class BackupEvolutionTests(unittest.TestCase):
    def _archive(self, directory: Path, name: str, entries: dict[str, bytes], timestamp: int) -> Path:
        path = directory / name
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for member, content in entries.items():
                bundle.writestr(member, content)
        import os

        os.utime(path, (timestamp, timestamp))
        return path

    def test_reports_added_modified_removed_and_exports_csv(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self._archive(
                directory,
                "one.zip",
                {"keep.txt": b"same", "edit.txt": b"old", "gone.txt": b"x"},
                1_700_000_000,
            )
            self._archive(
                directory,
                "two.zip",
                {"keep.txt": b"same", "edit.txt": b"new data", "new.txt": b"added"},
                1_700_000_100,
            )

            report = backup_evolution(directory)

            self.assertEqual(report["snapshots"], 2)
            self.assertEqual(report["change_count"], 3)
            transition = report["transitions"][0]
            self.assertEqual((transition["added"], transition["modified"], transition["removed"]), (1, 1, 1))
            self.assertTrue(evolution_has_changes(report))
            destination = directory / "report.csv"
            export_evolution_csv(report, destination)
            with destination.open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual({row["status"] for row in rows}, {"added", "modified", "removed"})

    def test_path_filter_and_no_change_detection(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            content = {"src/app.py": b"unchanged", "docs/readme.md": b"same"}
            self._archive(directory, "one.zip", content, 1_700_000_000)
            self._archive(directory, "two.zip", content, 1_700_000_100)
            report = backup_evolution(directory, "src/")
            self.assertEqual(report["change_count"], 0)
            self.assertFalse(evolution_has_changes(report))
            self.assertEqual(report["snapshots"], 2)


if __name__ == "__main__":
    unittest.main()
