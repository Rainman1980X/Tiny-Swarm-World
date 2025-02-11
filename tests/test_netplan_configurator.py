import unittest
from pathlib import Path

from ruamel.yaml import YAML

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
        # Test load raises error for missing file
        with self.assertRaises(FileNotFoundError):
            self.manager.load("non_existent_file.yaml")

    def test_validate(self):
        # Test YAML validation method
        data = {"key": "value"}
        with open(self.test_file, "w", encoding="utf-8") as file:
            self.yaml.dump(data, file)
        self.assertTrue(self.manager.validate(self.test_file))

    def test_validate_invalid_yaml(self):
        # Test invalid YAML detection
        with open(self.test_file, "w", encoding="utf-8") as file:
            file.write("invalid: [unbalanced_brackets")
        self.assertFalse(self.manager.validate(self.test_file))

    def test_save_and_load(self):
        # Test save and load functionality together
        data = {"network": {"version": 2}}
        self.manager.save(data, self.test_file)
        self.manager.load(self.test_file)
        self.assertEqual(self.manager.loaded_data, data)

    def test_load_sets_is_valid_false_on_error(self):
        # Test if load sets is_valid to False on error
        with open(self.test_file, "w", encoding="utf-8") as file:
            file.write("invalid: [unbalanced_brackets")
        with self.assertRaises(ValueError):
            self.manager.load(self.test_file)
        self.assertFalse(self.manager.is_valid)
