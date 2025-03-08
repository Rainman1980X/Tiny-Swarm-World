import unittest
from unittest.mock import AsyncMock, patch, MagicMock
from application.services.network.network_service import NetworkService
from domain.network.ip_value import IpValue


class TestNetworkService(unittest.IsolatedAsyncioTestCase):
    """Unit tests for the NetworkService class."""

    @patch("application.services.network.network_service.LoggerFactory")
    @patch("application.services.network.network_service.IpExtractorBuilder")
    @patch("application.services.network.network_service.CommandBuilder")
    @patch("application.services.network.network_service.PortVmRepositoryYaml")
    @patch("application.services.network.network_service.CommandRunnerUI")
    @patch("application.services.network.network_service.PortCommandRepositoryYaml")
    @patch("application.services.network.network_service.PortNetplanRepositoryYaml")
    async def test_run_calls_setup_commands_init_twice_and_returns_command_list(
        self,
        mock_netplan_repo_yaml,
        mock_command_repo_yaml,
        mock_runner_ui,
        mock_vm_repository,
        mock_command_builder,
        mock_ip_extractor_builder,
        mock_logger_factory
    ):
        """Tests that run() initializes network setup and calls dependencies correctly."""

        # Mock logger
        mock_logger = MagicMock()
        mock_logger_factory.get_logger.return_value = mock_logger

        # Mock CommandRunnerUI
        mock_runner_ui_instance = AsyncMock()
        mock_runner_ui.return_value = mock_runner_ui_instance
        mock_runner_ui_instance.run.return_value = [
            None,
            [
                "ignored_field_0",
                "ignored_field_1",
                "fake_data1 fake_data2 192.168.1.254",
                "192.168.1.1 some-other-data"
            ]
        ]

        # Mock CommandBuilder
        mock_command_builder_instance = MagicMock()
        mock_command_builder.return_value = mock_command_builder_instance
        mock_command_builder_instance.get_command_list.return_value = {"cmd1": {}, "cmd2": {}}

        # Mock IpExtractorBuilder
        mock_ip_extractor_instance = MagicMock()
        mock_ip_extractor_builder.return_value = mock_ip_extractor_instance
        mock_ip_extractor_instance.build.side_effect = [
            IpValue(ip_address="192.168.1.1"),  # Gateway als IpValue-Objekt
            IpValue(ip_address="10.0.0.1")  # IP als IpValue-Objekt
        ]

        # Mock VmRepository
        mock_vm_repository_instance = MagicMock()
        mock_vm_repository.return_value = mock_vm_repository_instance
        mock_vm_repository_instance.find_vm_instances_by_type.return_value = ["manager-vm"]

        # Mock PortNetplanRepositoryYaml
        mock_netplan_instance = MagicMock()
        mock_netplan_repo_yaml.return_value = mock_netplan_instance

        # Mock PortCommandRepositoryYaml
        mock_command_repo_instance = MagicMock()
        mock_command_repo_yaml.return_value = mock_command_repo_instance

        # Test NetworkService
        service = NetworkService()
        await service.run()

        # Assertions
        mock_logger.info.assert_called()
        mock_runner_ui_instance.run.assert_called_once()
        mock_ip_extractor_instance.build.assert_called()
        mock_vm_repository_instance.find_vm_instances_by_type.assert_called_once()
        mock_netplan_instance.create.assert_called_once()
        mock_netplan_instance.save.assert_called_once()
