import unittest
from unittest.mock import Mock, patch

from ruamel.yaml import YAML

from domain.network.ip_value import IpValue
from domain.network.network import Network
from infrastructure.adapters.exceptions.exception_yaml_handling import YAMLHandlingError
from infrastructure.adapters.repositories.netplan_repository import PortNetplanRepositoryYaml


class TestPortNetplanRepositoryYaml(unittest.TestCase):

    @patch("infrastructure.adapters.file_management.yaml.yaml_file_manager.YamlFileManager")
    def setUp(self, mock_yaml_manager):
        # Mock YamlFileManager
        self.mock_yaml_manager = mock_yaml_manager.return_value
        self.mock_yaml_manager.load.return_value = {"network": {"version": 2}}
        self.mock_yaml_manager.save = Mock()

        # Initialize NetplanRepository with mock
        self.manager = PortNetplanRepositoryYaml()
        self.manager.yaml_manager = self.mock_yaml_manager  # Inject mock manager

        # Test data
        self.test_network = Network(
            ip_address=IpValue(ip_address="192.168.1.10"),
            gateway=IpValue(ip_address="192.168.1.1"),
            vm_instance="test-vm"
        )
        self.yaml = YAML()
        self.yaml.default_flow_style = False

    def test_create(self):
        """Test if create() generates the correct YAML structure."""
        result = self.manager.create(self.test_network)
        self.assertIsInstance(result, dict)
        self.assertIn("network", result)
        self.assertEqual(result["network"]["version"], 2)

    def test_load_valid_yaml(self):
        """Test if load() correctly retrieves YAML data from YamlFileManager."""
        result = self.manager.load()
        self.assertEqual(result, {"network": {"version": 2}})
        self.mock_yaml_manager.load.assert_called_once()

    def test_load_file_not_found(self):
        """Test if load() handles missing files gracefully."""
        self.mock_yaml_manager.load.side_effect = FileNotFoundError("File not found")

        result = self.manager.load()
        self.assertEqual(result, {})  # Should return empty dict instead of error
        self.mock_yaml_manager.load.assert_called_once()

    def test_save_successful(self):
        """Test if save() correctly calls YamlFileManager.save()."""
        self.manager.builder = Mock()
        self.manager.builder.to_yaml.return_value = "mock_yaml_content"

        self.manager.save()

        self.manager.builder.to_yaml.assert_called_once()
        self.mock_yaml_manager.save.assert_called_once_with("mock_yaml_content")

    def test_save_failure_raises_yaml_handling_error(self):
        """Test if save() raises YAMLHandlingError on failure."""
        self.manager.builder = Mock()
        self.manager.builder.to_yaml.return_value = "mock_yaml_content"
        self.mock_yaml_manager.save.side_effect = Exception("Write error")

        with self.assertRaises(YAMLHandlingError) as context:
            self.manager.save()

        self.assertIn("Write error", str(context.exception))
        self.mock_yaml_manager.save.assert_called_once()


if __name__ == "__main__":
    unittest.main()
