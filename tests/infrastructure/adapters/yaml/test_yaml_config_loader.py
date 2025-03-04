import unittest
from unittest.mock import mock_open, patch

from ruamel.yaml import YAML, YAMLError
from ruamel.yaml.parser import ParserError
from ruamel.yaml.scanner import ScannerError

from infrastructure.adapters.exceptions.exception_yaml_handling import YAMLHandlingError
from infrastructure.adapters.file_management.yaml.yaml_file_loader import YamlFileLoader
from infrastructure.adapters.file_management.yaml.yaml_file_locator import YamlFileLocator


class TestYAMLFileLoader(unittest.TestCase):

    def setUp(self):
        self.valid_yaml_path = "valid_config.yaml"
        self.loader = YamlFileLoader(self.valid_yaml_path)

    @patch("builtins.open", new_callable=mock_open, read_data="key: value")
    @patch("infrastructure.adapters.file_management.yaml.yaml_file_locator.YamlFileLocator.find_file_path", return_value="mock_path")
    def test_load_valid_yaml(self, mock_find_path, mock_open_file):
        result = self.loader.load()
        self.assertEqual(result, {"key": "value"})

    @patch("builtins.open", side_effect=FileNotFoundError)
    @patch("infrastructure.adapters.file_management.yaml.yaml_file_locator.YamlFileLocator.find_file_path", return_value="mock_path")
    def test_load_file_not_found(self, mock_find_path, mock_open_file):
        with self.assertRaises(YAMLHandlingError) as context:
            self.loader.load()
        self.assertIn("FileNotFound", str(context.exception))

    @patch("builtins.open", new_callable=mock_open, read_data="")
    @patch("infrastructure.adapters.file_management.yaml.yaml_file_locator.YamlFileLocator.find_file_path", return_value="mock_path")
    def test_load_empty_yaml(self, mock_find_path, mock_open_file):
        with self.assertRaises(YAMLHandlingError) as context:
            self.loader.load()
        self.assertIn("empty or contains only whitespace", str(context.exception))

    @patch("builtins.open", new_callable=mock_open, read_data="---\nkey: [invalid_yaml")
    @patch("infrastructure.adapters.file_management.yaml.yaml_file_locator.YamlFileLocator.find_file_path", return_value="mock_path")
    @patch.object(YAML, "load", side_effect=ScannerError("YAML Scanner Error"))
    def test_load_scanner_error(self, mock_yaml_load, mock_find_path, mock_open_file):
        with self.assertRaises(YAMLHandlingError) as context:
            self.loader.load()
        self.assertIn("YAML Syntax Error", str(context.exception))

    @patch("builtins.open", new_callable=mock_open, read_data="key:\n    - value\n  -")
    @patch("infrastructure.adapters.file_management.yaml.yaml_file_locator.YamlFileLocator.find_file_path", return_value="mock_path")
    @patch.object(YAML, "load", side_effect=YAMLError("General YAML error"))
    def test_load_yaml_error(self, mock_yaml_load, mock_find_path, mock_open_file):
        with self.assertRaises(YAMLHandlingError) as context:
            self.loader.load()
        self.assertIn("General YAML error", str(context.exception))

    @patch("builtins.open", new_callable=mock_open, read_data="key: value")
    @patch("infrastructure.adapters.file_management.yaml.yaml_file_locator.YamlFileLocator.find_file_path", return_value="mock_path")
    @patch.object(YAML, "load", return_value="")
    def test_load_invalid_data_type(self, mock_yaml_load, mock_find_path, mock_open_file):
        with self.assertRaises(YAMLHandlingError) as context:
            self.loader.load()
        self.assertIn("The YAML file is empty or contains only whitespace.", str(context.exception))


if __name__ == "__main__":
    unittest.main()
