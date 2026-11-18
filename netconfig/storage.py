"""
Підсистема персистентного збереження та завантаження конфігурації (JSON, CSV, CONF, SH).
Використовує протокол менеджерів контексту `with`.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .exceptions import StorageError
from .manager import RouterConfigurator
from .models import NetworkInterface, StaticRoute, VlanInterface

__all__ = [
    "load_text_config",
    "save_to_json",
    "load_from_json",
    "save_to_csv",
    "save_script",
]


def load_text_config(filepath: str | Path) -> RouterConfigurator:
    """Читає текстовий файл конфігурації за допомогою менеджера контексту with."""
    path = Path(filepath)
    if not path.exists():
        raise StorageError(f"Вхідний файл конфігурації '{path}' не знайдено.")

    try:
        with open(path, "r", encoding="utf-8") as file:
            lines = file.readlines()
    except OSError as exc:
        raise StorageError(f"Помилка читання файлу '{path}': {exc}") from exc

    configurator = RouterConfigurator()
    configurator.parse_lines(lines)
    return configurator


def save_to_json(configurator: RouterConfigurator, filepath: str | Path) -> Path:
    """Зберігає поточний стан конфігуратора у формат JSON через with."""
    path = Path(filepath)
    payload = {
        "hostname": configurator.hostname,
        "interfaces": [iface.to_dict() for iface in configurator.get_sorted_interfaces()],
        "routes": [route.to_dict() for route in configurator.get_sorted_routes()],
    }

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=4)
    except OSError as exc:
        raise StorageError(f"Не вдалося зберегти JSON у '{path}': {exc}") from exc

    return path


def load_from_json(filepath: str | Path) -> RouterConfigurator:
    """Відновлює об'єктну модель RouterConfigurator із JSON-файлу."""
    path = Path(filepath)
    if not path.exists():
        raise StorageError(f"JSON-файл '{path}' не знайдено.")

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise StorageError(f"Помилка читання JSON-файлу '{path}': {exc}") from exc

    try:
        configurator = RouterConfigurator(hostname=data["hostname"])
        for item in data.get("interfaces", []):
            if item.get("type") == "VlanInterface":
                iface: NetworkInterface = VlanInterface(
                    name=item["name"],
                    parent_interface=item["parent_interface"],
                    vlan_id=item["vlan_id"],
                    ip_address=item["ip_address"],
                    prefix=item["prefix"],
                    mac_address=item["mac_address"],
                    mtu=item["mtu"],
                    bandwidth_mbps=item["bandwidth_mbps"],
                    enabled=item["enabled"],
                )
            else:
                iface = NetworkInterface(
                    name=item["name"],
                    ip_address=item["ip_address"],
                    prefix=item["prefix"],
                    mac_address=item["mac_address"],
                    mtu=item["mtu"],
                    bandwidth_mbps=item["bandwidth_mbps"],
                    enabled=item["enabled"],
                )
            configurator.add_interface(iface)

        for item in data.get("routes", []):
            route = StaticRoute(
                destination=item["destination"],
                prefix=item["prefix"],
                gateway=item["gateway"],
                interface_name=item["interface_name"],
                metric=item["metric"],
                name=item.get("name"),
                enabled=item["enabled"],
            )
            configurator.add_route(route)
    except KeyError as exc:
        raise StorageError(f"У JSON-файлі '{path}' відсутнє обов'язкове поле: {exc}") from exc

    return configurator


def save_to_csv(configurator: RouterConfigurator, filepath: str | Path) -> Path:
    """Експортує зведену таблицю інтерфейсів та маршрутів у CSV-файл через with."""
    path = Path(filepath)
    fieldnames = [
        "entity_type",
        "name",
        "address_cidr",
        "mac_or_gateway",
        "interface_or_parent",
        "mtu_or_metric",
        "bandwidth_mbps",
        "vlan_id",
        "enabled",
    ]

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()

            for iface in configurator.get_sorted_interfaces():
                is_vlan = isinstance(iface, VlanInterface)
                writer.writerow(
                    {
                        "entity_type": iface.__class__.__name__,
                        "name": iface.name,
                        "address_cidr": iface.cidr,
                        "mac_or_gateway": iface.mac_address,
                        "interface_or_parent": iface.parent_interface if is_vlan else "-",
                        "mtu_or_metric": iface.mtu,
                        "bandwidth_mbps": iface.bandwidth_mbps,
                        "vlan_id": iface.vlan_id if is_vlan else "-",
                        "enabled": iface.enabled,
                    }
                )

            for route in configurator.get_sorted_routes():
                writer.writerow(
                    {
                        "entity_type": "StaticRoute",
                        "name": route.name,
                        "address_cidr": route.cidr,
                        "mac_or_gateway": route.gateway,
                        "interface_or_parent": route.interface_name,
                        "mtu_or_metric": route.metric,
                        "bandwidth_mbps": "-",
                        "vlan_id": "-",
                        "enabled": route.enabled,
                    }
                )
    except OSError as exc:
        raise StorageError(f"Не вдалося зберегти CSV у '{path}': {exc}") from exc

    return path


def save_script(script_text: str, filepath: str | Path) -> Path:
    """Записує згенерований bash-скрипт у файл із закінченням рядків LF."""
    path = Path(filepath)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as file:
            file.write(script_text)
    except OSError as exc:
        raise StorageError(f"Не вдалося записати скрипт '{path}': {exc}") from exc

    return path