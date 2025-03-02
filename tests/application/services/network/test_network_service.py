import unittest
from unittest.mock import Mock, AsyncMock, patch

from application.ports.repositories.port_yaml_repository import PortYamlRepository
from application.services.network.network_service import NetworkService
from domain.network.network import Network


@patch("application.services.network.network_service.CommandRunnerUI")
@patch("application.services.network.network_service.PortNetplanRepositoryYaml")
class TestNetworkService(unittest.TestCase):

    def setUp(self):
        # Mock for PortYamlRepository
        self.mock_yaml_manager = Mock(spec=PortYamlRepository)
        self.mock_yaml_manager.create = Mock(return_value={"mock": "data"})
        self.mock_yaml_manager.save = Mock()
        self.mock_yaml_manager.load = Mock(return_value={})
        self.mock_yaml_manager.validate = Mock()

        # Mock for VM repository (return mock VM instances, e.g. ['swarm-manager'])
        self.mock_vm_repository = Mock()
        self.mock_vm_repository.find_vm_instances_by_type = Mock(return_value=["swarm-manager"])

        # Initialize NetworkService with mocked repositories
        with patch("application.services.network.network_service.PortVmRepositoryYaml",
                   return_value=self.mock_vm_repository):
            self.network_service = NetworkService()
            self.network_service.port = self.mock_yaml_manager

    async def test_run_creates_and_saves_data(self, mock_netplan_repo, mock_command_runner):
        # Mock setup for CommandRunnerUI and PortNetplanRepositoryYaml
        mock_runner_instance = AsyncMock()
        mock_runner_instance.run = AsyncMock(return_value="mocked-command-result")
        mock_command_runner.return_value = mock_runner_instance

        mock_netplan_instance = Mock()
        mock_netplan_instance.create = Mock()
        mock_netplan_instance.save = Mock()
        mock_netplan_repo.return_value = mock_netplan_instance

        # Run the service method
        await self.network_service.run()

        # Verify that methods were called with expected arguments
        self.mock_vm_repository.find_vm_instances_by_type.assert_called_once_with("manager")
        mock_netplan_instance.create.assert_called_once()  # Network data creation
        mock_netplan_instance.save.assert_called_once()  # Network data saved



if __name__ == "__main__":
    unittest.main()
