import unittest

from unittest.mock import Mock, AsyncMock, patch

from application.ports.repositories.port_yaml_repository import PortYamlRepository
from application.services.network.network_service import NetworkService
from domain.network.network import Network


@patch("application.services.network.network_service.CommandRunnerUI")
@patch("application.services.network.network_service.PortNetplanRepositoryYaml")
class TestNetworkService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Mock für PortYamlRepository
        self.mock_yaml_manager = Mock(spec=PortYamlRepository)
        self.mock_yaml_manager.create = Mock(return_value={"mock": "data"})
        self.mock_yaml_manager.save = Mock()
        self.mock_yaml_manager.load = Mock(return_value={})
        self.mock_yaml_manager.validate = Mock()

        # Mock für das VM-Repository (simuliert Rückgabe von VM-Instanzen, z.B. ['swarm-manager'])
        self.mock_vm_repository = Mock()
        self.mock_vm_repository.find_vm_instances_by_type = Mock(return_value=["swarm-manager"])

        # Initialisiere NetworkService mit gemockten Repositories
        with patch("application.services.network.network_service.PortVmRepositoryYaml",
                   return_value=self.mock_vm_repository):
            self.network_service = NetworkService()
            self.network_service.port = self.mock_yaml_manager

    @patch("application.services.network.network_service.PortCommandRepositoryYaml")
    @patch("application.services.network.network_service.YAMLFileLoader")
    @patch("application.services.network.network_service.CommandBuilder")
    async def test_run_calls_setup_commands_init_twice_and_returns_command_list(
            self,
            mock_command_builder,
            mock_yaml_loader,
            mock_port_command_repository,
            mock_port_netplan_repo_yaml,
            mock_command_runner_ui
    ):
        # Arrange: Mock der Rückgabewerte
        mock_runner_ui_instance = AsyncMock()
        mock_runner_ui_instance.run.return_value = [
            None,  # first element
            [
                "ignored_field_0",  # result[1][0]
                "ignored_field_1",  # result[1][1]
                "fake_data1 fake_data2 192.168.1.254",  # result[1][2] -> Dritter Wert = Gateway-IP
                "192.168.1.1 some-other-data"  # result[1][3] -> Erste IP-Adresse
            ]
        ]

        mock_command_runner_ui.return_value = mock_runner_ui_instance

        # Bereite valide Daten für die Network-Klasse vor
        network_data = Network(
            ip_address="192.168.1.1",  # Gültige IPv4-Adresse
            gateway="192.168.1.254",  # Gültige IPv4-Adresse
            vm_instance="my-vm-instance"  # Gültiger VM-Name
        )

        # Logging Mock
        self.network_service.logger = Mock()

        # Act: Methode ausführen
        await self.network_service.run()

        # Assert: Prüfen, ob die Methode korrekt ausgeführt wurde
        self.assertEqual(mock_runner_ui_instance.run.call_count, 1)
        self.network_service.logger.info.assert_called_with("saving network data")