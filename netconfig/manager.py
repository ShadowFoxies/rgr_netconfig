"""
Модуль управління мережевою конфігурацією та генерації скриптів маршрутизації.
"""

from __future__ import annotations

import re

from .exceptions import (
    DuplicateEntityError,
    RoutingError,
    UnreachableGatewayError,
    ValidationError,
)
from .models import NetworkInterface, StaticRoute, VlanInterface

__all__ = ["RouterConfigurator"]

# Шаблони для розбору рядків текстового конфігураційного файлу
_HOST_LINE_RE = re.compile(r"^HOST\s+(\S+)$", re.IGNORECASE)
_IFACE_LINE_RE = re.compile(
    r"^IFACE\s+(\S+)\s+(\d+\.\d+\.\d+\.\d+)/(\d{1,2})\s+(\S+)"
    r"(?:\s+mtu=(\d+))?(?:\s+bw=(\d+))?(?:\s+(up|down))?$",
    re.IGNORECASE,
)
_VLAN_LINE_RE = re.compile(
    r"^VLAN\s+(\S+)\s+parent=(\S+)\s+vlan=(\d+)\s+(\d+\.\d+\.\d+\.\d+)/(\d{1,2})\s+(\S+)"
    r"(?:\s+mtu=(\d+))?(?:\s+bw=(\d+))?(?:\s+(up|down))?$",
    re.IGNORECASE,
)
_ROUTE_LINE_RE = re.compile(
    r"^ROUTE\s+(\d+\.\d+\.\d+\.\d+)/(\d{1,2})\s+via\s+(\d+\.\d+\.\d+\.\d+)\s+dev\s+(\S+)"
    r"(?:\s+metric=(\d+))?(?:\s+(up|down))?$",
    re.IGNORECASE,
)


class RouterConfigurator:
    """Головний конфігуратор інтерфейсів та таблиці статичної маршрутизації."""

    def __init__(self, hostname: str = "router-01") -> None:
        self.__hostname = ""
        self.hostname = hostname
        self.__interfaces: dict[str, NetworkInterface] = {}
        self.__routes: list[StaticRoute] = []
        self.__route_keys: set[tuple[str, int, str, str]] = set()

    @property
    def hostname(self) -> str:
        """Ім'я мережевого вузла (маршрутизатора)."""
        return self.__hostname

    @hostname.setter
    def hostname(self, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValidationError("Ім'я вузла (hostname) не може бути порожнім.")
        self.__hostname = value.strip()

    @property
    def interfaces(self) -> list[NetworkInterface]:
        """Список усіх зареєстрованих інтерфейсів."""
        return list(self.__interfaces.values())

    @property
    def routes(self) -> list[StaticRoute]:
        """Список усіх зареєстрованих статичних маршрутів."""
        return list(self.__routes)

    def add_interface(self, interface: NetworkInterface) -> None:
        """Додає інтерфейс із перевіркою на дублювання імені."""
        if interface.name in self.__interfaces:
            raise DuplicateEntityError(
                f"Інтерфейс '{interface.name}' вже існує у конфігурації."
            )
        self.__interfaces[interface.name] = interface

    def get_interface(self, name: str) -> NetworkInterface:
        """Повертає інтерфейс за іменем або підіймає виняток."""
        if name not in self.__interfaces:
            raise RoutingError(f"Інтерфейс '{name}' не знайдено у конфігурації.")
        return self.__interfaces[name]

    def add_route(self, route: StaticRoute) -> None:
        """
        Додає статичний маршрут із перевіркою:
        1) відсутності дублікатів;
        2) існування та активності вихідного інтерфейсу;
        3) досяжності шлюзу (gateway) у підмережі інтерфейсу.
        """
        key = (route.destination, route.prefix, route.gateway, route.interface_name)
        if key in self.__route_keys:
            raise DuplicateEntityError(
                f"Маршрут {route.cidr} через {route.gateway} ({route.interface_name}) вже існує."
            )

        iface = self.get_interface(route.interface_name)
        if not iface.enabled:
            raise UnreachableGatewayError(
                f"Інтерфейс '{iface.name}' вимкнено (DOWN): шлюз {route.gateway} недосяжний."
            )
        if not iface.contains_ip(route.gateway):
            raise UnreachableGatewayError(
                f"Шлюз {route.gateway} не належить підмережі інтерфейсу '{iface.name}' ({iface.cidr})."
            )

        self.__route_keys.add(key)
        self.__routes.append(route)

    def get_sorted_interfaces(self) -> list[NetworkInterface]:
        """Повертає інтерфейси, відсортовані за IP-адресою та іменем (__lt__)."""
        return sorted(self.__interfaces.values())

    def get_sorted_routes(self) -> list[StaticRoute]:
        """Повертає маршрути, відсортовані за метрикою (__lt__)."""
        return sorted(self.__routes)

    def total_enabled_bandwidth_mbps(self) -> int:
        """Обчислює сумарну пропускну здатність активних інтерфейсів (через __add__)."""
        enabled_ifaces = [iface for iface in self.__interfaces.values() if iface.enabled]
        return sum(enabled_ifaces, 0)

    def generate_script(self) -> str:
        """Генерує готовий bash-скрипт конфігурування інтерфейсів та маршрутів."""
        lines = [
            "#!/bin/bash",
            f"# Автоматично згенерований скрипт конфігурації вузла: {self.__hostname}",
            "set -e",
            "",
            "# === 1. Налаштування мережевих інтерфейсів ===",
        ]
        for iface in self.get_sorted_interfaces():
            lines.extend(iface.generate_commands())

        lines.append("")
        lines.append("# === 2. Налаштування таблиці статичної маршрутизації ===")
        for route in self.get_sorted_routes():
            lines.extend(route.generate_commands())

        lines.append("")
        lines.append(f'echo "Конфігурацію вузла {self.__hostname} успішно застосовано."')
        return "\n".join(lines) + "\n"

    def parse_lines(self, lines: list[str]) -> None:
        """Розбирає рядки текстової конфігурації та наповнює модель."""
        for line_no, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            if host_match := _HOST_LINE_RE.match(line):
                self.hostname = host_match.group(1)
                continue

            if iface_match := _IFACE_LINE_RE.match(line):
                name, ip, prefix, mac, mtu, bw, state = iface_match.groups()
                iface = NetworkInterface(
                    name=name,
                    ip_address=ip,
                    prefix=int(prefix),
                    mac_address=mac,
                    mtu=int(mtu) if mtu else 1500,
                    bandwidth_mbps=int(bw) if bw else 1000,
                    enabled=(state.lower() != "down") if state else True,
                )
                self.add_interface(iface)
                continue

            if vlan_match := _VLAN_LINE_RE.match(line):
                name, parent, vlan_id, ip, prefix, mac, mtu, bw, state = vlan_match.groups()
                vlan_iface = VlanInterface(
                    name=name,
                    parent_interface=parent,
                    vlan_id=int(vlan_id),
                    ip_address=ip,
                    prefix=int(prefix),
                    mac_address=mac,
                    mtu=int(mtu) if mtu else 1500,
                    bandwidth_mbps=int(bw) if bw else 1000,
                    enabled=(state.lower() != "down") if state else True,
                )
                self.add_interface(vlan_iface)
                continue

            if route_match := _ROUTE_LINE_RE.match(line):
                dest, prefix, gw, dev, metric, state = route_match.groups()
                route = StaticRoute(
                    destination=dest,
                    prefix=int(prefix),
                    gateway=gw,
                    interface_name=dev,
                    metric=int(metric) if metric else 100,
                    enabled=(state.lower() != "down") if state else True,
                )
                self.add_route(route)
                continue

            raise ValidationError(
                f"Рядок {line_no}: нерозпізнаний формат директиви -> '{line}'"
            )