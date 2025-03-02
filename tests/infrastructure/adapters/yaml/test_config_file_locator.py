import unittest
from unittest.mock import patch

from docker.infrastructure.adapters.yaml.config_file_locator import ConfigFileLocator


class TestConfigFileLocator(unittest.TestCase):

    def setUp(self):
        self.filename = "test_config.yaml"
        self.locator = ConfigFileLocator(self.filename)

    @patch("os.getcwd", return_value="/current")  # Mock `os.getcwd()`
    @patch("os.path.isdir")
    @patch("os.path.isfile")
    def test_find_file_path_in_default_directory(self, mock_isfile, mock_isdir, mock_getcwd):
        """
        Test if `ConfigFileLocator` correctly finds the configuration file in the default directory.
        """
        locator = ConfigFileLocator(self.filename)

        normalized_default_path = locator._normalize_to_linux_path("/current/config")
        normalized_file_path = locator._normalize_to_linux_path(f"/current/config/{self.filename}")

        mock_isdir.side_effect = lambda path: path == normalized_default_path
        mock_isfile.side_effect = lambda path: path == normalized_file_path

        resolved_path = locator.find_file_path()
        self.assertEqual(resolved_path, normalized_file_path)

    @patch("os.path.isdir")
    @patch("os.path.isfile")
    @patch("os.path.abspath")
    @patch("os.path.dirname")
    def test_find_file_path_in_script_directory(self, mock_dirname, mock_abspath, mock_isfile, mock_isdir):
        """
        Test if `ConfigFileLocator` correctly finds the configuration file in the script directory.
        """
        script_dir = "/mocked/script_directory"
        mock_abspath.return_value = f"{script_dir}/config_file_locator.py"
        mock_dirname.return_value = script_dir

        expected_script_config_dir = f"{script_dir}/config"
        expected_file_path = f"{script_dir}/config/{self.filename}"

        normalized_script_dir = ConfigFileLocator._normalize_to_linux_path(script_dir)
        normalized_script_config_dir = ConfigFileLocator._normalize_to_linux_path(expected_script_config_dir)
        normalized_file_path = ConfigFileLocator._normalize_to_linux_path(expected_file_path)

        mock_isdir.side_effect = lambda path: path in [normalized_script_dir, normalized_script_config_dir]
        mock_isfile.side_effect = lambda path: path == normalized_file_path

        locator = ConfigFileLocator(self.filename)
        locator.search_paths.insert(1, normalized_script_config_dir)

        print(f"Locator search paths: {locator.search_paths}")

        resolved_path = locator.find_file_path()
        self.assertEqual(resolved_path, normalized_file_path)

    @patch("os.path.isdir", return_value=False)
    @patch("os.path.isfile", return_value=False)
    def test_file_not_found_raises_exception(self, mock_isfile, mock_isdir):
        with self.assertRaises(FileNotFoundError):
            self.locator.find_file_path()

    @patch("os.getcwd", return_value="/mocked/project")
    @patch("os.path.isdir")
    @patch("os.path.isfile")
    def test_find_file_path_additional_paths(self, mock_isfile, mock_isdir, mock_getcwd):
        """
        Test if `ConfigFileLocator` correctly finds a configuration file in additional paths.
        """
        additional_path = "/custom/path"
        locator_with_extra_path = ConfigFileLocator(self.filename, additional_paths=[additional_path])

        normalized_additional_path = locator_with_extra_path._normalize_to_linux_path(additional_path)
        normalized_default_path = locator_with_extra_path._normalize_to_linux_path("/mocked/project/config")
        normalized_file_path = locator_with_extra_path._normalize_to_linux_path(f"{additional_path}/{self.filename}")

        mock_isdir.side_effect = lambda path: path in [
            normalized_additional_path,
            normalized_default_path
        ]
        mock_isfile.side_effect = lambda path: path == normalized_file_path

        resolved_path = locator_with_extra_path.find_file_path()
        self.assertEqual(resolved_path, normalized_file_path)

    @patch("os.path.isdir")
    @patch("os.path.isfile")
    def test_find_file_path_non_default_directory(self, mock_isfile, mock_isdir):
        mock_isdir.side_effect = lambda path: path == "/non/default"
        mock_isfile.side_effect = lambda path: path == "/non/default/test_config.yaml"

        locator_non_default = ConfigFileLocator(self.filename, additional_paths=["/non/default"])
        resolved_path = locator_non_default.find_file_path()

        expected_path = "/non/default/test_config.yaml"
        self.assertEqual(resolved_path, expected_path)


if __name__ == "__main__":
    unittest.main()
