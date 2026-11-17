"""
Об'єктно-орієнтована модель мережевих інтерфейсів та статичних маршрутів.
Реалізує наслідування, інкапсуляцію (@property), поліморфізм та dunder-методи.
"""

from __future__ import annotations

from .exceptions import ValidationError
from .validators import (
    get_network_address,
    ip_to_int,
    is_ip_in_subnet,
    normalize_interface_name,
    normalize_prefix,
    prefix_to_netmask,
    validate_ipv4,
    validate_mac,
    validate_vlan,
)

__all__ = [
    "NetworkEntity",
    "NetworkInterface",
    "VlanInterface",
    "StaticRoute",
]


class NetworkEntity:
    """Базовий клас для всіх мережевих конфігураційних сутностей."""

    def __init__(self, name: str, enabled: bool = True) -> None:
        self.__name = ""
        self.__enabled = True
        self.name = name
        self.enabled = enabled

    @property
    def name(self) -> str:
        """Ім'я або ідентифікатор сутності."""
        return self.__name

    @name.setter
    def name(self, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValidationError("Ім'я мережевої сутності не може бути порожнім.")
        self.__name = value.strip()

    @property
    def enabled(self) -> bool:
        """Стан активності сутності (увімкнено/вимкнено)."""
        return self.__enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise ValidationError("Параметр enabled повинен мати логічний тип bool.")
        self.__enabled = value

    def generate_commands(self) -> list[str]:
        """Поліморфний метод генерації команд конфігурації ОС."""
        raise NotImplementedError("Похідний клас повинен реалізувати generate_commands().")

    def to_dict(self) -> dict:
        """Серіалізація базових полів сутності у словник."""
        return {
            "type": self.__class__.__name__,
            "name": self.__name,
            "enabled": self.__enabled,
        }

    def __str__(self) -> str:
        state = "UP" if self.__enabled else "DOWN"
        return f"[{state}] {self.__name}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.__name!r}, enabled={self.__enabled!r})"


class NetworkInterface(NetworkEntity):
    """Модель фізичного або віртуального мережевого інтерфейсу."""

    def __init__(
        self,
        name: str,
        ip_address: str,
        prefix: str | int = 24,
        mac_address: str = "00:00:00:00:00:00",
        mtu: int = 1500,
        bandwidth_mbps: int = 1000,
        enabled: bool = True,
    ) -> None:
        super().__init__(normalize_interface_name(name), enabled)
        self.__ip_address = ""
        self.__prefix = 24
        self.__mac_address = ""
        self.__mtu = 1500
        self.__bandwidth_mbps = 1000

        self.ip_address = ip_address
        self.prefix = prefix
        self.mac_address = mac_address
        self.mtu = mtu
        self.bandwidth_mbps = bandwidth_mbps

    @NetworkEntity.name.setter
    def name(self, value: str) -> None:
        NetworkEntity.name.fset(self, normalize_interface_name(value))

    @property
    def ip_address(self) -> str:
        """IPv4-адреса інтерфейсу."""
        return self.__ip_address

    @ip_address.setter
    def ip_address(self, value: str) -> None:
        self.__ip_address = validate_ipv4(value)

    @property
    def prefix(self) -> int:
        """Довжина префікса підмережі CIDR (0..32)."""
        return self.__prefix

    @prefix.setter
    def prefix(self, value: str | int) -> None:
        self.__prefix = normalize_prefix(value)

    @property
    def mac_address(self) -> str:
        """Фізична MAC-адреса інтерфейсу."""
        return self.__mac_address

    @mac_address.setter
    def mac_address(self, value: str) -> None:
        self.__mac_address = validate_mac(value)

    @property
    def mtu(self) -> int:
        """Максимальний розмір пакета (MTU) у байтах."""
        return self.__mtu

    @mtu.setter
    def mtu(self, value: int) -> None:
        if isinstance(value, bool) or not isinstance(value, int) or not 68 <= value <= 9000:
            raise ValidationError(f"Неприпустимий MTU '{value}': очікується ціле число від 68 до 9000.")
        self.__mtu = value

    @property
    def bandwidth_mbps(self) -> int:
        """Номінальна пропускна здатність каналу в Мбіт/с."""
        return self.__bandwidth_mbps

    @bandwidth_mbps.setter
    def bandwidth_mbps(self, value: int) -> None:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValidationError(f"Неприпустима пропускна здатність '{value}': очікується число > 0.")
        self.__bandwidth_mbps = value

    @property
    def netmask(self) -> str:
        """Десяткова маска підмережі, обчислена з префікса."""
        return prefix_to_netmask(self.__prefix)

    @property
    def network_address(self) -> str:
        """Адреса мережі, до якої належить інтерфейс."""
        return get_network_address(self.__ip_address, self.__prefix)

    @property
    def cidr(self) -> str:
        """Адреса у нотації IP/prefix."""
        return f"{self.__ip_address}/{self.__prefix}"

    def contains_ip(self, target_ip: str) -> bool:
        """Перевіряє, чи знаходиться цільова IP-адреса в локальній підмережі інтерфейсу."""
        return is_ip_in_subnet(target_ip, self.__ip_address, self.__prefix)

    def generate_commands(self) -> list[str]:
        """Генерує команди налаштування інтерфейсу для утиліти ip (Linux iproute2)."""
        commands = [
            f"ip link set dev {self.name} mtu {self.__mtu}",
            f"ip addr replace {self.cidr} dev {self.name}",
            f"ip link set dev {self.name} {'up' if self.enabled else 'down'}",
        ]
        return commands

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update(
            {
                "ip_address": self.__ip_address,
                "prefix": self.__prefix,
                "mac_address": self.__mac_address,
                "mtu": self.__mtu,
                "bandwidth_mbps": self.__bandwidth_mbps,
            }
        )
        return data

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NetworkInterface):
            return NotImplemented
        return (
            self.name == other.name
            and self.__ip_address == other.__ip_address
            and self.__prefix == other.__prefix
        )

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, NetworkInterface):
            return NotImplemented
        return (ip_to_int(self.__ip_address), self.name) < (ip_to_int(other.__ip_address), other.name)

    def __add__(self, other: object) -> int:
        """Обчислює сумарну пропускну здатність при агрегації інтерфейсів (Мбіт/с)."""
        if isinstance(other, NetworkInterface):
            return self.__bandwidth_mbps + other.__bandwidth_mbps
        if isinstance(other, int) and not isinstance(other, bool):
            return self.__bandwidth_mbps + other
        return NotImplemented

    def __radd__(self, other: object) -> int:
        return self.__add__(other)

    def __str__(self) -> str:
        state = "UP" if self.enabled else "DOWN"
        return (
            f"[{state}] {self.name}: {self.cidr} "
            f"(MAC: {self.__mac_address}, MTU: {self.__mtu}, {self.__bandwidth_mbps} Mbps)"
        )

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(name={self.name!r}, ip_address={self.__ip_address!r}, "
            f"prefix={self.__prefix!r}, mac_address={self.__mac_address!r}, "
            f"mtu={self.__mtu!r}, bandwidth_mbps={self.__bandwidth_mbps!r}, enabled={self.enabled!r})"
        )


class VlanInterface(NetworkInterface):
    """Модель логічного 802.1Q VLAN-інтерфейсу поверх фізичного інтерфейсу."""

    def __init__(
        self,
        name: str,
        parent_interface: str,
        vlan_id: int,
        ip_address: str,
        prefix: str | int = 24,
        mac_address: str = "00:00:00:00:00:00",
        mtu: int = 1500,
        bandwidth_mbps: int = 1000,
        enabled: bool = True,
    ) -> None:
        super().__init__(
            name=name,
            ip_address=ip_address,
            prefix=prefix,
            mac_address=mac_address,
            mtu=mtu,
            bandwidth_mbps=bandwidth_mbps,
            enabled=enabled,
        )
        self.__parent_interface = ""
        self.__vlan_id = 1
        self.parent_interface = parent_interface
        self.vlan_id = vlan_id

    @property
    def parent_interface(self) -> str:
        """Фізичний батьківський інтерфейс (наприклад, eth0)."""
        return self.__parent_interface

    @parent_interface.setter
    def parent_interface(self, value: str) -> None:
        self.__parent_interface = normalize_interface_name(value)

    @property
    def vlan_id(self) -> int:
        """Тег 802.1Q VLAN ID (1..4094)."""
        return self.__vlan_id

    @vlan_id.setter
    def vlan_id(self, value: int) -> None:
        self.__vlan_id = validate_vlan(value)

    def generate_commands(self) -> list[str]:
        """Поліморфно додає команду створення VLAN-підінтерфейсу."""
        commands = [
            f"ip link add link {self.__parent_interface} name {self.name} type vlan id {self.__vlan_id}"
        ]
        commands.extend(super().generate_commands())
        return commands

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update(
            {
                "parent_interface": self.__parent_interface,
                "vlan_id": self.__vlan_id,
            }
        )
        return data

    def __str__(self) -> str:
        return f"{super().__str__()} [VLAN {self.__vlan_id} -> {self.__parent_interface}]"

    def __repr__(self) -> str:
        return (
            f"VlanInterface(name={self.name!r}, parent_interface={self.__parent_interface!r}, "
            f"vlan_id={self.__vlan_id!r}, ip_address={self.ip_address!r}, prefix={self.prefix!r}, "
            f"enabled={self.enabled!r})"
        )


class StaticRoute(NetworkEntity):
    """Модель запису статичної маршрутизації IPv4."""

    def __init__(
        self,
        destination: str,
        prefix: str | int,
        gateway: str,
        interface_name: str,
        metric: int = 100,
        name: str | None = None,
        enabled: bool = True,
    ) -> None:
        self.__prefix = normalize_prefix(prefix)
        self.__destination = get_network_address(destination, self.__prefix)
        self.__gateway = ""
        self.__interface_name = ""
        self.__metric = 100

        route_label = name if name else f"route_{self.__destination}/{self.__prefix}"
        super().__init__(route_label, enabled)

        self.gateway = gateway
        self.interface_name = interface_name
        self.metric = metric

    @property
    def destination(self) -> str:
        """Адреса цільової мережі."""
        return self.__destination

    @destination.setter
    def destination(self, value: str) -> None:
        self.__destination = get_network_address(value, self.__prefix)

    @property
    def prefix(self) -> int:
        """Префікс цільової підмережі (0..32)."""
        return self.__prefix

    @prefix.setter
    def prefix(self, value: str | int) -> None:
        self.__prefix = normalize_prefix(value)
        self.__destination = get_network_address(self.__destination, self.__prefix)

    @property
    def gateway(self) -> str:
        """IPv4-адреса наступного переходу (next-hop gateway)."""
        return self.__gateway

    @gateway.setter
    def gateway(self, value: str) -> None:
        self.__gateway = validate_ipv4(value)

    @property
    def interface_name(self) -> str:
        """Ім'я вихідного інтерфейсу."""
        return self.__interface_name

    @interface_name.setter
    def interface_name(self, value: str) -> None:
        self.__interface_name = normalize_interface_name(value)

    @property
    def metric(self) -> int:
        """Метрика маршруту (менше значення означає вищий пріоритет)."""
        return self.__metric

    @metric.setter
    def metric(self, value: int) -> None:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValidationError(f"Неприпустима метрика '{value}': очікується ціле число >= 0.")
        self.__metric = value

    @property
    def cidr(self) -> str:
        """Цільова мережа у форматі CIDR."""
        return f"{self.__destination}/{self.__prefix}"

    def generate_commands(self) -> list[str]:
        """Генерує команду додавання або видалення статичного маршруту."""
        if not self.enabled:
            return [f"# Маршрут {self.cidr} через {self.__gateway} вимкнено"]
        return [
            f"ip route replace {self.cidr} via {self.__gateway} "
            f"dev {self.__interface_name} metric {self.__metric}"
        ]

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update(
            {
                "destination": self.__destination,
                "prefix": self.__prefix,
                "gateway": self.__gateway,
                "interface_name": self.__interface_name,
                "metric": self.__metric,
            }
        )
        return data

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, StaticRoute):
            return NotImplemented
        return (
            self.__destination == other.__destination
            and self.__prefix == other.__prefix
            and self.__gateway == other.__gateway
            and self.__interface_name == other.__interface_name
        )

    def __lt__(self, other: object) -> bool:
        """Порівняння маршрутів за пріоритетом (метрикою) для таблиці маршрутизації."""
        if not isinstance(other, StaticRoute):
            return NotImplemented
        return (self.__metric, -self.__prefix, ip_to_int(self.__destination)) < (
            other.__metric,
            -other.__prefix,
            ip_to_int(other.__destination),
        )

    def __add__(self, delta: int) -> StaticRoute:
        """Повертає копію маршруту зі збільшеною метрикою (для резервних маршрутів)."""
        if isinstance(delta, bool) or not isinstance(delta, int):
            return NotImplemented
        return StaticRoute(
            destination=self.__destination,
            prefix=self.__prefix,
            gateway=self.__gateway,
            interface_name=self.__interface_name,
            metric=self.__metric + delta,
            name=f"{self.name}_backup",
            enabled=self.enabled,
        )

    def __sub__(self, delta: int) -> StaticRoute:
        """Повертає копію маршруту зі зменшеною метрикою."""
        if isinstance(delta, bool) or not isinstance(delta, int):
            return NotImplemented
        return StaticRoute(
            destination=self.__destination,
            prefix=self.__prefix,
            gateway=self.__gateway,
            interface_name=self.__interface_name,
            metric=self.__metric - delta,
            name=self.name,
            enabled=self.enabled,
        )

    def __str__(self) -> str:
        state = "ACTIVE" if self.enabled else "DISABLED"
        return (
            f"[{state}] {self.cidr} -> via {self.__gateway} "
            f"dev {self.__interface_name} (metric {self.__metric})"
        )

    def __repr__(self) -> str:
        return (
            f"StaticRoute(destination={self.__destination!r}, prefix={self.__prefix!r}, "
            f"gateway={self.__gateway!r}, interface_name={self.__interface_name!r}, "
            f"metric={self.__metric!r}, enabled={self.enabled!r})"
        )