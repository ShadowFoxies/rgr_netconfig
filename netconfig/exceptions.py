"""
Модуль користувацьких винятків для підсистеми мережевого конфігурування.
Освітній компонент: Програмування на Python. Базовий рівень.
"""

__all__ = [
    "NetConfigError",
    "ValidationError",
    "InvalidIPAddressError",
    "InvalidMaskError",
    "InvalidMACError",
    "InvalidVLANError",
    "RoutingError",
    "UnreachableGatewayError",
    "DuplicateEntityError",
    "StorageError",
]


class NetConfigError(Exception):
    """Базовий виняток для всіх аварійних станів модуля netconfig."""


class ValidationError(NetConfigError):
    """Помилка валідації вхідних мережевих параметрів."""


class InvalidIPAddressError(ValidationError):
    """Некоректний формат або діапазон октетів IPv4-адреси."""

    def __init__(self, ip_address: str, reason: str = "некоректний формат IPv4") -> None:
        self.ip_address = ip_address
        super().__init__(f"Неприпустима IP-адреса '{ip_address}': {reason}")


class InvalidMaskError(ValidationError):
    """Некоректна маска підмережі або префікс CIDR."""

    def __init__(self, mask: str | int, reason: str = "очікується префікс 0..32 або коректна маска") -> None:
        self.mask = mask
        super().__init__(f"Неприпустима маска '{mask}': {reason}")


class InvalidMACError(ValidationError):
    """Некоректний формат фізичної MAC-адреси."""

    def __init__(self, mac: str) -> None:
        self.mac = mac
        super().__init__(f"Неприпустима MAC-адреса '{mac}' (очікується формат XX:XX:XX:XX:XX:XX)")


class InvalidVLANError(ValidationError):
    """Некоректний ідентифікатор VLAN (допустимий діапазон 1..4094)."""

    def __init__(self, vlan_id: int) -> None:
        self.vlan_id = vlan_id
        super().__init__(f"Неприпустимий VLAN ID '{vlan_id}': допустимі значення від 1 до 4094")


class RoutingError(NetConfigError):
    """Помилки логіки маршрутизації та конфліктів конфігурації."""


class UnreachableGatewayError(RoutingError):
    """Шлюз не належить до жодної локальної підмережі активних інтерфейсів."""


class DuplicateEntityError(RoutingError):
    """Спроба повторного додавання інтерфейсу або маршруту."""


class StorageError(NetConfigError):
    """Помилка читання або запису файлів конфігурації (JSON/CSV)."""