import os
import unittest
from pathlib import Path

from infrastructure.adapters.file_management.path_normalizer import PathNormalizer


class TestPathNormalizer(unittest.TestCase):
    def setUp(self):
        self.test_path = "test/directory/../file.txt"
        self.path_normalizer = PathNormalizer(self.test_path)

    def test_normalize_returns_normalized_path(self):
        """
        Test if normalize() correctly resolves and normalizes paths.
        """
        normalized_path = self.path_normalizer.normalize()
        expected_path = PathNormalizer(str(Path(self.test_path).resolve())).normalize()  # Normalize expected path

        self.assertEqual(normalized_path, expected_path)

    def test_ensure_directory_creates_directory(self):
        """
        Test if ensure_directory() correctly creates directories.
        """
        test_directory = "test_temp_dir"
        test_path = os.path.join(test_directory, "subdir")
        normalizer = PathNormalizer(test_path)

        normalizer.ensure_directory()
        self.assertTrue(os.path.isdir(test_path))

        # Cleanup
        if os.path.exists(test_path):
            os.rmdir(test_path)
        if os.path.exists(test_directory):
            os.rmdir(test_directory)

    def test_basename_returns_correct_name(self):
        """
        Test if basename() correctly extracts the filename.
        """
        expected_basename = "file.txt"
        basename = self.path_normalizer.basename()
        self.assertEqual(expected_basename, basename)

    def test_parent_directory_returns_correct_parent_path(self):
        """
        Test if parent_directory() correctly returns the parent directory.
        """
        expected_parent = PathNormalizer(self.test_path).parent_directory()  # Get normalized parent
        parent_directory = self.path_normalizer.parent_directory()

        self.assertEqual(parent_directory, expected_parent)

    def test_normalize_handles_drive_letters(self):
        """
        Test if normalize() correctly handles Windows drive letters.
        """
        if os.name == "nt":  # Only run this test on Windows
            windows_path = "C:\\Users\\test\\file.txt"
            normalizer = PathNormalizer(windows_path)
            expected_path = "/Users/test/file.txt"  # Expected Linux-style path
            normalized_path = normalizer.normalize()
            self.assertEqual(normalized_path, expected_path)


if __name__ == "__main__":
    unittest.main()
