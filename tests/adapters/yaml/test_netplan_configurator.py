import unittest
from pathlib import Path
from unittest.mock import mock_open, patch, Mock

from ruamel.yaml import YAML

from docker.adapters.exceptions.exception_yaml_handling import YAMLHandlingError
from docker.adapters.yaml.netplan_configurator import NetplanConfigurationManager
from docker.domain.network.network import Network


class TestNetplanConfigurationManager(unittest.TestCase):

    def setUp(self):
        # Create a new instance of NetplanConfigurationManager
        self.manager = NetplanConfigurationManager()
        self.test_file = "cloud-init-manager.yaml"
        self.test_network = Network(
            ip_address="192.168.1.10",
            gateway="192.168.1.1",
            vm_instance="test-vm"
        )
        self.yaml = YAML()
        self.yaml.default_flow_style = False

    def tearDown(self):
        # Clean up test files if they exist
        if Path(self.test_file).exists():
            Path(self.test_file).unlink()

    def test_create(self):
        # Test if create generates the correct structure
        result = self.manager.create(self.test_network)
        self.assertIsInstance(result, dict)
        self.assertIn("network", result)
        self.assertEqual(result["network"]["version"], 2)

    @patch("os.path.exists", return_value=False)
    def test_load_file_not_found(self, mock_exists):
        with self.assertRaises(YAMLHandlingError) as cm:
            self.manager.load("non_existent_file.yaml")
        self.assertIn("does not exist", str(cm.exception))
        mock_exists.assert_called_once_with("non_existent_file.yaml")

    @patch("os.path.exists", return_value=True)
    @patch("os.path.getsize", return_value=0)
    def test_load_empty_file(self, mock_getsize, mock_exists):
        with self.assertRaises(YAMLHandlingError) as cm:
            self.manager.load("empty_file.yaml")
        self.assertIn("is empty", str(cm.exception))
        mock_exists.assert_called_once_with("empty_file.yaml")
        mock_getsize.assert_called_once_with("empty_file.yaml")

    @patch("os.path.exists", return_value=True)
    @patch("os.path.getsize", return_value=1)
    def test_load_invalid_extension(self, mock_getsize, mock_exists):
        with self.assertRaises(YAMLHandlingError) as cm:
            self.manager.load("invalid_file.txt")
        self.assertIn("Unsupported file extension", str(cm.exception))
        mock_exists.assert_called_once_with("invalid_file.txt")
        mock_getsize.assert_called_once_with("invalid_file.txt")

    @patch("os.path.exists", return_value=True)
    @patch("os.path.getsize", return_value=1)
    @patch("builtins.open", new_callable=mock_open, read_data="invalid: :yaml")
    @patch("ruamel.yaml.YAML.load", side_effect=Exception("Invalid YAML"))
    def test_load_invalid_yaml(self, mock_yaml_load, mock_open_file, mock_getsize, mock_exists):
        with self.assertRaises(YAMLHandlingError) as cm:
            self.manager.load("invalid_yaml.yaml")
        self.assertIn("Invalid YAML", str(cm.exception))  # Adjust expected message here
        mock_exists.assert_called_once_with("invalid_yaml.yaml")
        mock_getsize.assert_called_once_with("invalid_yaml.yaml")
        mock_open_file.assert_called_once_with("invalid_yaml.yaml", "r", encoding="utf-8")
        mock_yaml_load.assert_called_once()

    @patch("os.path.exists", return_value=True)
    @patch("os.path.getsize", return_value=1)
    @patch("builtins.open", new_callable=mock_open, read_data="valid: yaml")
    @patch("ruamel.yaml.YAML.load", return_value={"valid": "yaml"})
    def test_load_valid_yaml(self, mock_yaml_load, mock_open_file, mock_getsize, mock_exists):
        self.manager.load("valid_yaml.yaml")
        self.assertTrue(self.manager.is_valid)
        self.assertEqual(self.manager.loaded_data, {"valid": "yaml"})
        mock_exists.assert_called_once_with("valid_yaml.yaml")
        mock_getsize.assert_called_once_with("valid_yaml.yaml")
        mock_open_file.assert_called_once_with("valid_yaml.yaml", "r", encoding="utf-8")
        mock_yaml_load.assert_called_once()

    @patch("builtins.open", new_callable=mock_open)
    def test_save_file_success(self, mock_file):
        # Create a local mock for to_yaml
        self.manager.builder = Mock()  # Mock the builder component
        self.manager.builder.to_yaml = Mock(return_value="mock_yaml_content")  # Mock the `to_yaml` method

        file_path = "cloud-init-manager.yaml"
        self.manager.save(file_path=file_path)

        # Assertions
        self.manager.builder.to_yaml.assert_called_once()  # Ensure `to_yaml` was called once
        mock_file.assert_called_once_with(file_path, "w", encoding="utf-8")  # Ensure `open` was called correctly
        mock_file().write.assert_called_once_with("mock_yaml_content")  # Ensure the correct content was written

    @patch("builtins.open", new_callable=mock_open)
    def test_save_with_default_file_name(self, mock_file):
        # Create a local mock for to_yaml
        self.manager.builder = Mock()  # Mock the builder component
        self.manager.builder.to_yaml = Mock(return_value="mock_yaml_content")  # Mock the `to_yaml` method

        # Execute the test
        self.manager.save()

        # Assertions
        self.manager.builder.to_yaml.assert_called_once()  # Ensure `to_yaml` was called once
        mock_file.assert_called_once_with(self.test_file, "w",
                                          encoding="utf-8")  # Ensure default file name was written
        mock_file().write.assert_called_once_with("mock_yaml_content")  # Ensure correct content was written

    @patch("builtins.open", side_effect=Exception("Some error"))
    def test_save_failure_raises_yaml_handling_error(self, mock_file):
        with self.assertRaises(YAMLHandlingError) as context:
            self.manager.save()
        self.assertEqual(context.exception.file_name, self.test_file)
        self.assertIn("Some error", str(context.exception))

    def test_str_with_all_details(self):
        file_name = "config.yaml"
        error = ValueError("Invalid value")
        exception = YAMLHandlingError(file_name, error)

        expected_output = (
            f"YAMLLoadError: Error while loading '{file_name}'\n"
            f"Error Type: {type(error).__name__}\n"
            f"Details: {str(error)}"
        )
        self.assertEqual(str(exception), expected_output)

    def test_str_without_details(self):
        file_name = "config.yaml"
        error = Exception()
        exception = YAMLHandlingError(file_name, error)

        expected_output = (
            f"YAMLLoadError: Error while loading '{file_name}'\n"
            f"Error Type: {type(error).__name__}\n"
            f"Details: No additional details"
        )
        self.assertEqual(str(exception), expected_output)
