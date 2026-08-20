import os
import unittest
from unittest.mock import patch

from codesaver.cli import build_parser
from codesaver.lang import SUPPORTED_LANGUAGES, TRANSLATIONS, detect_language, normalize_language, translate


class LocalizationTests(unittest.TestCase):
    def test_every_language_has_every_message(self):
        keys = set(TRANSLATIONS["en"])
        self.assertEqual(set(TRANSLATIONS), set(SUPPORTED_LANGUAGES))
        for language in SUPPORTED_LANGUAGES:
            self.assertEqual(set(TRANSLATIONS[language]), keys, language)

    def test_locale_detection_supports_region_and_falls_back(self):
        self.assertEqual(normalize_language("uk_UA.UTF-8"), "uk")
        self.assertEqual(normalize_language("de-DE"), "de")
        self.assertEqual(normalize_language("unknown_LOCALE"), "en")
        with patch.dict(os.environ, {"LC_ALL": "ja_JP.UTF-8"}, clear=True):
            self.assertEqual(detect_language(), "ja")

    def test_help_can_be_rendered_in_each_language(self):
        for language in SUPPORTED_LANGUAGES:
            help_text = build_parser(language).format_help()
            self.assertIn(translate("help.description", language), help_text)
            self.assertIn("--backup-now", help_text)
            self.assertIn("--exclude-ext", help_text)
            self.assertIn("--keep-days", help_text)
            self.assertIn("--follow-symlinks", help_text)


if __name__ == "__main__":
    unittest.main()
