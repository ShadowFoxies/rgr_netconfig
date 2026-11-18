"""
Модульні тести для пакета netconfig (валідація, ООП, маршрутизація, JSON/CSV).
"""

import json
import tempfile
import unittest
from pathlib import Path

from netconfig import (
    DuplicateEntityError,
    InvalidIPAddressError,
    InvalidMACError,
    InvalidMaskError,
    InvalidVLANError,
    NetworkInterface,
    RouterConfigurator,
    StaticRoute,
    StorageError,
    UnreachableGatewayError,
    VlanInterface,
    load_from_json,
    normalize_prefix,
    save_to_csv,
    save_to_json,
    validate_mac,
)


class TestValidators(unittest.TestCase):
    """Тести регулярних виразів та мережевих валідаторів."""

    def test_valid_and_invalid_prefix(self) -> None:
        self.assertEqual(normalize_prefix("255.255.255.0"), 24)
        self.assertEqual(normalize_prefix("/16"), 16)
        with self.assertRaises(InvalidMaskError):
            normalize_prefix("255.0.255.0")  # Небезперервна маска

    def test_mac_normalization_and_error(self) -> None:
        self.assertEqual(validate_mac("aa-bb-cc-11-22-33"), "AA:BB:CC:11:22:33")
        with self.assertRaises(InvalidMACError):
            validate_mac("ZZ:BB:CC:11:22:33")

    def test_invalid_ip_and_vlan(self) -> None:
        with self.assertRaises(InvalidIPAddressError):
            NetworkInterface("eth0", "999.1.1.1", 24)
        with self.assertRaises(InvalidVLANError):
            VlanInterface("eth0.5000", "eth0", 5000, "192.168.1.1", 24)


class TestModelsAndDunder(unittest.TestCase):
    """Тести ООП-ієрархії, інкапсуляції та магічних методів."""

    def test_interface_addition_and_comparison(self) -> None:
        eth0 = NetworkInterface("eth0", "192.168.1.1", 24, bandwidth_mbps=1000)
        eth1 = NetworkInterface("eth1", "10.0.0.1", 24, bandwidth_mbps=2500)
        self.assertEqual(eth0 + eth1, 3500)
        self.assertTrue(eth1 < eth0)

    def test_static_route_arithmetic_and_sorting(self) -> None:
        primary = StaticRoute("172.16.5.99", 16, "192.168.1.254", "eth0", metric=10)
        self.assertEqual(primary.destination, "172.16.0.0")  # Автонормалізація адреси мережі
        backup = primary + 90
        self.assertEqual(backup.metric, 100)
        self.assertTrue(primary < backup)

    def test_vlan_polymorphism(self) -> None:
        vlan = VlanInterface("eth0.10", "eth0", 10, "10.10.10.1", 24)
        cmds = vlan.generate_commands()
        self.assertTrue(cmds[0].startswith("ip link add link eth0 name eth0.10 type vlan id 10"))


class TestConfiguratorAndStorage(unittest.TestCase):
    """Тести маршрутної логіки та серіалізації JSON/CSV."""

    def test_unreachable_gateway_and_duplicates(self) -> None:
        rc = RouterConfigurator("test-gw")
        rc.add_interface(NetworkInterface("eth0", "192.168.1.1", 24))

        with self.assertRaises(DuplicateEntityError):
            rc.add_interface(NetworkInterface("eth0", "192.168.2.1", 24))

        with self.assertRaises(UnreachableGatewayError):
            rc.add_route(StaticRoute("10.0.0.0", 8, "172.16.0.254", "eth0"))

    def test_json_and_csv_persistence(self) -> None:
        rc = RouterConfigurator("persist-gw")
        rc.add_interface(NetworkInterface("eth0", "192.168.10.1", 24))
        rc.add_interface(VlanInterface("eth0.20", "eth0", 20, "192.168.20.1", 24))
        rc.add_route(StaticRoute("10.10.0.0", 16, "192.168.10.254", "eth0", metric=15))

        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "cfg.json"
            csv_path = Path(tmp) / "cfg.csv"

            save_to_json(rc, json_path)
            save_to_csv(rc, csv_path)

            restored = load_from_json(json_path)
            self.assertEqual(restored.hostname, "persist-gw")
            self.assertEqual(len(restored.interfaces), 2)
            self.assertEqual(len(restored.routes), 1)
            self.assertTrue(csv_path.exists())
            self.assertIn("VlanInterface", json.loads(json_path.read_text(encoding="utf-8"))["interfaces"][1]["type"])

    def test_missing_json_raises_storage_error(self) -> None:
        with self.assertRaises(StorageError):
            load_from_json("non_existent_file.json")


if __name__ == "__main__":
    unittest.main()