import unittest
from unittest.mock import Mock

from application.ports.repositories.port_yaml_repository import PortYamlRepository
from application.services.network.network_service import NetworkService
from domain.network.network import Network


class TestNetworkService(unittest.TestCase):

    def setUp(self):
        # Mock the methods from the abstract YamlManager
        self.mock_yaml_manager = Mock(spec=PortYamlRepository)
        self.mock_yaml_manager.create = Mock(return_value={"mock": "data"})
        self.mock_yaml_manager.save = Mock()
        self.mock_yaml_manager.load = Mock(return_value={})
        self.mock_yaml_manager.validate = Mock()

        # Initialize NetworkService with the mocked YamlManager
        self.network_service = NetworkService()
        self.network_service.port = self.mock_yaml_manager

    def test_run_creates_and_saves_data(self):
        mock_network = Mock(spec=Network)
        mock_data = {"mock": "data"}

        # Run the service method
        self.network_service.run()

        # Assert that create and save were called with the correct arguments
        self.mock_yaml_manager.create.assert_called_once_with(mock_network)
        self.mock_yaml_manager.save.assert_called_once_with(mock_data, "cloud-init-manager.yaml")


if __name__ == "__main__":
    unittest.main()
