import csv
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from codesaver.backup_metadata import BackupMetadataStore
from codesaver.cli import _handle_backup_workflows, build_parser
from codesaver.core import BackupManager


class BackupMetadataTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.backups = self.root / "backups"
        self.backups.mkdir()
        self.archive = self.backups / "project-2026-10-13.zip"
        with zipfile.ZipFile(self.archive, "w") as bundle:
            bundle.writestr("src/main.py", "print('hi')")
        self.store = BackupMetadataStore(self.backups)

    def tearDown(self):
        self.temporary.cleanup()

    def test_labels_and_notes_persist_and_search_case_insensitively(self):
        self.store.update(self.archive, label="release", note="Before migration")
        self.assertEqual(self.store.get(self.archive), {"label": "release", "note": "Before migration"})
        self.assertEqual([row["archive"] for row in self.store.catalog("MIGRATION")], [self.archive.name])
        self.assertEqual(self.store.catalog("absent"), [])

    def test_catalog_exports_csv_and_json_with_annotations(self):
        self.store.update(self.archive, label="stable", note="Ready")
        csv_path = self.root / "catalog.csv"
        json_path = self.root / "catalog.json"
        self.assertEqual(self.store.export(csv_path), 1)
        self.assertEqual(self.store.export(json_path), 1)
        with csv_path.open(encoding="utf-8-sig", newline="") as stream:
            self.assertEqual(next(csv.DictReader(stream))["label"], "stable")
        self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["archives"][0]["note"], "Ready")
        with self.assertRaises(ValueError):
            self.store.export(self.archive)
        with self.assertRaises(ValueError):
            self.store.export(self.store.index_path)

    def test_rejects_outside_archives_and_invalid_index(self):
        outside = self.root / "outside.zip"
        outside.touch()
        with self.assertRaises(ValueError):
            self.store.update(outside, label="bad")
        self.store.index_path.write_text("{}", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.store.catalog()

    def test_cli_metadata_commands_update_search_and_export(self):
        manager = BackupManager(self.root, self.backups)
        commands = (
            ["--backup-label", self.archive.name, "nightly"],
            ["--backup-note", self.archive.name, "Before migration"],
            ["--backup-metadata-search", "migration"],
            ["--backup-catalog-export", str(self.root / "cli-catalog.csv")],
        )
        for command in commands:
            args = build_parser("en").parse_args(command)
            self.assertTrue(_handle_backup_workflows(args, manager))
        self.assertEqual(self.store.get(self.archive), {"label": "nightly", "note": "Before migration"})
        self.assertTrue((self.root / "cli-catalog.csv").is_file())


if __name__ == "__main__":
    unittest.main()
