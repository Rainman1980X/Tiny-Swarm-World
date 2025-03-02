import unittest
from unittest.mock import mock_open, patch

from ruamel.yaml import YAML, YAMLError

from infrastructure.adapters.exceptions.exception_yaml_handling import YAMLHandlingError
from infrastructure.adapters.yaml.yaml_config_loader import YAMLFileLoader


class TestYAMLFileLoader(unittest.TestCase):

    def setUp(self):
        self.valid_yaml_path = "valid_config.yaml"
        self.invalid_yaml_path = "invalid_config.yaml"
        self.empty_yaml_path = "empty_config.yaml"
        self.loader = YAMLFileLoader(self.valid_yaml_path)

    @patch("builtins.open", new_callable=mock_open, read_data="key: value")
    @patch("infrastructure.adapters.yaml.yaml_config_loader.ConfigFileLocator.find_file_path", return_value="mock_path")
    def test_load_valid_yaml(self, mock_find_path, mock_open_file):
        result = self.loader.load()
        self.assertEqual(result, {"key": "value"})

    @patch("builtins.open", side_effect=FileNotFoundError)
    @patch("infrastructure.adapters.yaml.yaml_config_loader.ConfigFileLocator.find_file_path", return_value="mock_path")
    def test_load_file_not_found(self, mock_find_path, mock_open_file):
        with self.assertRaises(YAMLHandlingError) as context:
            self.loader.load()
        self.assertEqual(context.exception.error_type, "FileNotFound")

    @patch("builtins.open", new_callable=mock_open, read_data="")
    @patch("infrastructure.adapters.yaml.yaml_config_loader.ConfigFileLocator.find_file_path", return_value="mock_path")
    def test_load_empty_yaml(self, mock_find_path, mock_open_file):
        with self.assertRaises(YAMLHandlingError) as context:
            self.loader.load()
        self.assertEqual(context.exception.error_type, "EmptyOrInvalidYAML")

    @patch("builtins.open", new_callable=mock_open, read_data="---\nkey: [invalid_yaml")
    @patch("infrastructure.adapters.yaml.yaml_config_loader.ConfigFileLocator.find_file_path", return_value="mock_path")
    def test_load_scanner_error(self, mock_find_path, mock_open_file):
        with self.assertRaises(YAMLHandlingError) as context:
            self.loader.load()
        self.assertEqual(context.exception.error_type, "YAMLParserError")

    @patch("builtins.open", new_callable=mock_open, read_data="key:\n    - value\n  -")
    @patch("infrastructure.adapters.yaml.yaml_config_loader.ConfigFileLocator.find_file_path", return_value="mock_path")
    @patch.object(YAML, "load", side_effect=YAMLError("General YAML error"))
    def test_load_yaml_error(self, mock_load, mock_find_path, mock_open_file):
        with self.assertRaises(YAMLHandlingError) as context:
            self.loader.load()
        self.assertEqual(context.exception.error_type, "YAMLLoadError")

    @patch("builtins.open", new_callable=mock_open, read_data="key: value")
    @patch("infrastructure.adapters.yaml.yaml_config_loader.ConfigFileLocator.find_file_path", return_value="mock_path")
    @patch("infrastructure.adapters.yaml.yaml_config_loader.YAML.load", return_value="")
    def test_load_invalid_data_type(self, mock_load, mock_find_path, mock_open_file):
        with self.assertRaises(YAMLHandlingError) as context:
            self.loader.load()
        self.assertEqual(context.exception.error_type, "EmptyOrInvalidYAML")


if __name__ == "__main__":
    unittest.main()
