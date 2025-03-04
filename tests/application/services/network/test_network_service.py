import unittest
from unittest.mock import Mock, AsyncMock, patch

from application.services.network.network_service import NetworkService
from infrastructure.adapters.file_management.yaml.yaml_file_manager import YamlFileManager


@patch("application.services.network.network_service.CommandRunnerUI")
@patch("application.services.network.network_service.PortNetplanRepositoryYaml")
@patch("application.services.network.network_service.YamlFileManager")
class TestNetworkService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Mock YamlFileManager
        self.mock_yaml_manager = Mock(spec=YamlFileManager)
        self.mock_yaml_manager.load.return_value = {"mock": "data"}
        self.mock_yaml_manager.save = Mock()

        # Mock VM-Repository
        self.mock_vm_repository = Mock()
        self.mock_vm_repository.find_vm_instances_by_type = Mock(return_value=["swarm-manager"])

        # Patch PortVmRepositoryYaml
        with patch("application.services.network.network_service.PortVmRepositoryYaml",
                   return_value=self.mock_vm_repository):
            self.network_service = NetworkService()

    @patch("application.services.network.network_service.PortCommandRepositoryYaml")
    async def test_run_calls_setup_commands_init_twice_and_returns_command_list(
            self,
            mock_port_command_repository,
            mock_yaml_manager,
            mock_port_netplan_repo_yaml,
            mock_command_runner_ui
    ):
        # Arrange: Mock runner UI behavior
        mock_runner_ui_instance = AsyncMock()
        mock_runner_ui_instance.run.return_value = [
            None,
            [
                "ignored_field_0",
                "ignored_field_1",
                "fake_data1 fake_data2 192.168.1.254",
                "192.168.1.1 some-other-data"
            ]
        ]
        mock_command_runner_ui.return_value = mock_runner_ui_instance

        # Mock Repository
        mock_netplan_repo_instance = mock_port_netplan_repo_yaml.return_value
        mock_netplan_repo_instance.create = Mock()
        mock_netplan_repo_instance.save = Mock()

        # Logging Mock
        self.network_service.logger = Mock()

        # Act: Run the async method
        await self.network_service.run()

        # Assert: Ensure that network data was saved
        self.assertEqual(mock_runner_ui_instance.run.call_count, 1)
        mock_netplan_repo_instance.create.assert_called_once()
        mock_netplan_repo_instance.save.assert_called_once()
        self.network_service.logger.info.assert_called_with("saving network data")
