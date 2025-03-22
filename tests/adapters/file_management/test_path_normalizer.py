import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from infrastructure.adapters.file_management.path_normalizer import PathNormalizer


class TestPathNormalizer(unittest.TestCase):
    def setUp(self):
        self.test_path = Path("test/directory/../file.txt").resolve().as_posix()

        # Patch PathFactory globally for all test methods
        self.path_factory_patcher = patch("infrastructure.adapters.file_management.path_normalizer.PathFactory")
        self.mock_path_factory_class = self.path_factory_patcher.start()
        self.addCleanup(self.path_factory_patcher.stop)  # ensures cleanup after each test

        # Mock the strategy
        self.mock_strategy = MagicMock()
        self.mock_strategy.normalize.return_value = self.test_path

        # Mock the factory to return that strategy
        self.mock_factory_instance = MagicMock()
        self.mock_factory_instance.get_strategy.return_value = self.mock_strategy
        self.mock_path_factory_class.return_value = self.mock_factory_instance

        # Temporary directories for directory tests
        self.temp_dir = "test_temp_dir"
        self.sub_dir = os.path.join(self.temp_dir, "subdir")

    def tearDown(self):
        # Cleanup created test directories
        if os.path.exists(self.sub_dir):
            os.rmdir(self.sub_dir)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)


    def test_normalize_returns_normalized_path(self):
        """
        Test if normalize() correctly resolves and normalizes paths.
        """
        normalizer = PathNormalizer(self.mock_factory_instance,self.test_path)

        normalized_path = normalizer.normalize()
        expected_path = Path(self.test_path).resolve().as_posix()
        self.assertEqual(normalized_path, expected_path)

    def test_ensure_directory_creates_directory(self):
        """
        Test if ensure_directory() correctly creates directories.
        """

        normalizer = PathNormalizer(self.mock_factory_instance, self.sub_dir)
        result = normalizer.ensure_directory()
        self.assertTrue(os.path.isdir(result))

    def test_basename_returns_correct_name(self):
        """
        Test if basename() correctly extracts the filename.
        """
        expected_basename = "file.txt"
        normalizer = PathNormalizer(self.mock_factory_instance, self.test_path)
        basename = normalizer.basename()
        self.assertEqual(expected_basename, basename)

    def test_parent_directory_returns_correct_path(self):
        """
        Test if parent_directory() correctly returns the parent directory.
        """
        normalizer = PathNormalizer(self.mock_factory_instance, self.test_path)
        expected_parent = Path(self.test_path).parent.as_posix()
        parent_directory = normalizer.parent_directory()

        self.assertEqual(parent_directory, expected_parent)

    @patch("infrastructure.adapters.file_management.path_normalizer.Path.mkdir")
    @patch("infrastructure.adapters.file_management.path_normalizer.Path.exists", return_value=False)
    def test_ensure_directory_creates_if_not_exists(self, mock_exists, mock_mkdir):
        """
        Test that ensure_directory() calls mkdir when the directory does not exist.
        """
        normalizer = PathNormalizer(self.mock_factory_instance, self.sub_dir)
        normalizer.ensure_directory()

        mock_exists.assert_called_once()
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch("infrastructure.adapters.file_management.path_normalizer.Path.mkdir")
    @patch("infrastructure.adapters.file_management.path_normalizer.Path.exists", return_value=True)
    def test_ensure_directory_skips_creation_if_exists(self, mock_exists, mock_mkdir):
        """
        Test that ensure_directory() does not call mkdir if directory already exists.
        """
        normalizer = PathNormalizer(self.mock_factory_instance, self.sub_dir)
        normalizer.ensure_directory()

        mock_exists.assert_called_once()
        mock_mkdir.assert_not_called()



if __name__ == "__main__":
    unittest.main()
