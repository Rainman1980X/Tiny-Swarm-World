import unittest
from unittest.mock import MagicMock, patch

from domain.multipass.vm_entity import VmEntity
from domain.multipass.vm_type import VmType
from infrastructure.adapters.repositories.vm_repository_yaml import PortVmRepositoryYaml


class TestPortVmRepositoryYaml(unittest.TestCase):

    def setUp(self):
        # Mock YamlFileManager
        patcher = patch("infrastructure.adapters.file_management.yaml.yaml_file_manager.YamlFileManager")
        self.mock_file_manager = patcher.start()
        self.addCleanup(patcher.stop)  # Ensure the patch is stopped after each test

        # Configure mock behavior
        self.mock_file_manager_instance = self.mock_file_manager.return_value
        self.mock_file_manager_instance.load.return_value = {
            "vms": [
                {"vm_instance": "vm1", "vm_type": VmType.MANAGER.value},
                {"vm_instance": "vm2", "vm_type": VmType.WORKER.value},
            ]
        }

        # Initialize repository with mocked YamlFileManager
        self.repo = PortVmRepositoryYaml(yaml_file_manager=self.mock_file_manager_instance)

    def test_get_all_vms(self):
        vms = self.repo.get_all_vms()
        self.assertEqual(len(vms), 2)
        self.assertEqual("vm1", vms[0].vm_instance)
        self.assertEqual(VmType.MANAGER.value, vms[0].vm_type.value)

    def test_get_vm_by_name_found(self):
        self.mock_file_manager_instance.load.return_value = {
            "vms": [
                {"vm_instance": "vm1"},
                {"vm_instance": "vm2"}
            ]
        }
        vm = self.repo.get_vm_by_name("vm1")
        self.assertIsNotNone(vm)
        self.assertEqual(vm.vm_instance, "vm1")

    def test_get_vm_by_name_not_found(self):
        self.mock_file_manager_instance.load.return_value = {"vms": []}
        vm = self.repo.get_vm_by_name("vm3")
        self.assertIsNone(vm)

    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_save(self, mock_open):
        self.repo.yaml_builder.to_yaml = MagicMock(return_value="yaml_data")

        # Call save method
        self.repo.save()

        # Verify that save was called on YamlFileManager
        self.mock_file_manager_instance.save.assert_called_once_with("yaml_data")

    def test_add_vm(self):
        mock_vm = VmEntity(vm_instance="vm3", vm_type=VmType.MANAGER, ipaddress="192.168.1.3", gateway="192.168.1.1")
        self.repo.yaml_builder.navigate_to = MagicMock(return_value=self.repo.yaml_builder)
        self.repo.yaml_builder.current.add_child = MagicMock()
        self.repo.save = MagicMock()
        self.repo.add_vm(mock_vm)
        self.repo.yaml_builder.navigate_to.assert_called_once_with(["vms"])
        self.repo.yaml_builder.current.add_child.assert_called_once_with(mock_vm.model_dump())
        self.repo.save.assert_called_once()

    def test_remove_vm_found(self):
        self.repo.yaml_builder.navigate_to = MagicMock(return_value=self.repo.yaml_builder)
        self.repo.yaml_builder.delete_current = MagicMock()
        self.repo.save = MagicMock()

        self.repo.remove_vm("vm1")

        self.repo.yaml_builder.navigate_to.assert_called_with(["vms", "vm_instance", "vm1"])
        self.repo.yaml_builder.delete_current.assert_called_once()
        self.repo.save.assert_called_once()

    def test_remove_vm_not_found(self):
        self.mock_file_manager_instance.load.return_value = {"vms": []}
        with self.assertRaises(ValueError) as context:
            self.repo.remove_vm("nonexistent_vm")
        self.assertEqual(str(context.exception), "VM nonexistent_vm not found.")

    def test_find_vm_instances_by_type(self):
        self.mock_file_manager_instance.load.return_value = {
            "vms": [
                {"vm_instance": "vm1", "vm_type": VmType.MANAGER.value},
                {"vm_instance": "vm2", "vm_type": VmType.WORKER.value},
            ]
        }

        repo = PortVmRepositoryYaml(yaml_file_manager=self.mock_file_manager_instance)
        vm_instances = repo.find_vm_instances_by_type(VmType.MANAGER)

        self.assertEqual(["vm1"], vm_instances)


if __name__ == "__main__":
    unittest.main()
