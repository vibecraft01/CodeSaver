import unittest

from codesaver.runtime import check_python_version, python_version_text


class RuntimeTests(unittest.TestCase):
    def test_supported_python_versions(self):
        self.assertFalse(check_python_version((3, 8)))
        self.assertTrue(check_python_version((3, 9)))
        self.assertTrue(check_python_version((3, 12)))
        self.assertEqual(python_version_text((3, 9)), "3.9")


if __name__ == "__main__":
    unittest.main()
