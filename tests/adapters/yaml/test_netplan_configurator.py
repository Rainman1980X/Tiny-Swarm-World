import unittest
from pathlib import Path

from ruamel.yaml import YAML

from docker.adapters.exceptions.exception_yaml_handling import YAMLHandlingError
from docker.adapters.yaml.netplan_configurator import NetplanConfigurationManager
from docker.domain.network.network import Network


class TestNetplanConfigurationManager(unittest.TestCase):

    def setUp(self):
        # Create a new instance of NetplanConfigurationManager
        self.manager = NetplanConfigurationManager()
        self.test_file = "test_netplan.yaml"
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

    def test_save(self):
        # Test saving functionality
        data = {"key": "value"}
        self.manager.save(data, self.test_file)
        self.assertTrue(Path(self.test_file).exists())
        with open(self.test_file, "r", encoding="utf-8") as file:
            loaded_data = self.yaml.load(file)
        self.assertEqual(loaded_data, data)

    def test_load(self):
        # Test loading functionality
        data = {"key": "value"}
        with open(self.test_file, "w", encoding="utf-8") as file:
            self.yaml.dump(data, file)
        self.manager.load(self.test_file)
        self.assertEqual(self.manager.loaded_data, data)
        self.assertTrue(self.manager.is_valid)

    def test_load_missing_file(self):
        # Test load raises YAMLHandlingError for missing file
        with self.assertRaises(YAMLHandlingError) as context:
            self.manager.load("non_existent_file.yaml")

        exception = context.exception
        self.assertEqual(exception.error_type, "Exception")
        self.assertIn("does not exist", str(exception))

    def test_validate_valid_yaml(self):
        """Ensure that valid YAML files are correctly validated."""
        data = {"key": "value"}
        with open(self.test_file, "w", encoding="utf-8") as file:
            self.yaml.dump(data, file)  # Fixed inconsistent YAML usage
        self.assertTrue(self.manager.validate(self.test_file))

    def test_validate_invalid_yaml(self):
        """Ensure that invalid YAML files raise YAMLLoadError."""
        with open(self.test_file, "w", encoding="utf-8") as file:
            file.write("invalid: [unbalanced_brackets")  # Malformed YAML

        with self.assertRaises(YAMLHandlingError) as context:
            self.manager.validate(self.test_file)

        self.assertEqual(context.exception.error_type, "YAMLSyntaxError")
        self.assertIn("while parsing", context.exception.args[0])  # Adjusted for actual usage

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

    def test_save_default_file_name(self):
        """Test saving functionality using the default file_name."""
        data = {"key": "value"}
        self.manager.save(data)
        self.assertTrue(Path(self.manager.file_name).exists())

        with open(self.manager.file_name, "r", encoding="utf-8") as file:
            loaded_data = self.yaml.load(file)
        self.assertEqual(loaded_data, data)

    def test_load_invalid_extension(self):
        """Test load raises error for unsupported file format."""
        invalid_file = "invalid_file.txt"
        with open(invalid_file, "w", encoding="utf-8") as file:
            file.write("invalid format")

        with self.assertRaises(YAMLHandlingError) as context:
            self.manager.load(invalid_file)

        self.assertIn("Failed to load file", str(context.exception))
        # Clean up test file
        Path(invalid_file).unlink()

    def test_load_empty_file(self):
        """Test loading an empty YAML file."""
        empty_file = "empty_file.yaml"
        Path(empty_file).touch()

        with self.assertRaises(YAMLHandlingError) as context:
            self.manager.load(empty_file)

        self.assertIn("Failed to load file", str(context.exception))
        # Clean up test file
        Path(empty_file).unlink()
