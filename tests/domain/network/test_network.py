import unittest
import uuid

from domain.network.network import Network


class TestNetwork(unittest.TestCase):

    def test_network_initialization(self):
        network = Network(
            ip_address="192.168.0.1",
            gateway="192.168.0.254",
            vm_instance="vm-123"
        )
        self.assertIsInstance(network.id, uuid.UUID)
        self.assertEqual(network.ip_address, "192.168.0.1")
        self.assertEqual(network.gateway, "192.168.0.254")
        self.assertEqual(network.vm_instance, "vm-123")

    def test_validate_ip_address_valid(self):
        network = Network(
            ip_address="10.0.0.1",
            gateway="10.0.0.254",
            vm_instance="vm-456"
        )
        self.assertEqual(network.ip_address, "10.0.0.1")

    def test_validate_ip_address_invalid(self):
        with self.assertRaises(ValueError) as context:
            Network(
                ip_address="invalid_ip",
                gateway="10.0.0.254",
                vm_instance="vm-789"
            )
        self.assertIn("Invalid IP address", str(context.exception))

    def test_validate_gateway_valid(self):
        network = Network(
            ip_address="172.16.0.1",
            gateway="172.16.0.254",
            vm_instance="vm-321"
        )
        self.assertEqual(network.gateway, "172.16.0.254")

    def test_validate_gateway_invalid(self):
        with self.assertRaises(ValueError) as context:
            Network(
                ip_address="192.168.1.1",
                gateway="not_an_ip",
                vm_instance="vm-invalid"
            )
        self.assertIn("Invalid IP address", str(context.exception))

    def test_validate_vm_instance_valid(self):
        network = Network(
            ip_address="8.8.8.8",
            gateway="8.8.4.4",
            vm_instance="vm-999"
        )
        self.assertEqual(network.vm_instance, "vm-999")

    def test_validate_vm_instance_empty(self):
        with self.assertRaises(ValueError) as context:
            Network(
                ip_address="127.0.0.1",
                gateway="127.0.0.254",
                vm_instance=""
            )
        self.assertIn("VM instance cannot be empty", str(context.exception))

    def test_validate_vm_instance_whitespace_only(self):
        with self.assertRaises(ValueError) as context:
            Network(
                ip_address="192.168.10.1",
                gateway="192.168.10.254",
                vm_instance="   "
            )
        self.assertIn("VM instance cannot be empty", str(context.exception))
