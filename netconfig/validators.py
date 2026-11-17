"""
Модуль валідації та нормалізації мережевих параметрів.
Використовує регулярні вирази (re), методи рядків та бітові операції IPv4.
"""

import re

from .exceptions import (
    InvalidIPAddressError,
    InvalidMACError,
    InvalidMaskError,
    InvalidVLANError,
    ValidationError,
)

__all__ = [
    "normalize_interface_name",
    "validate_ipv4",
    "ip_to_int",
    "int_to_ip",
    "normalize_prefix",
    "prefix_to_netmask",
    "get_network_address",
    "is_ip_in_subnet",
    "validate_mac",
    "validate_vlan",
]

# Регулярні вирази для перевірки мережевих форматів
_IFACE_NAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9._/-]{0,15}$")
_IPV4_RE = re.compile(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$")
_CIDR_RE = re.compile(r"^/?(\d{1,2})$")
_MAC_RE = re.compile(r"^([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}$")


def normalize_interface_name(name: str) -> str:
    """Перевіряє та нормалізує ім'я мережевого інтерфейсу."""
    if not isinstance(name, str):
        raise ValidationError("Ім'я інтерфейсу повинно бути рядком.")
    cleaned = name.strip()
    if not _IFACE_NAME_RE.match(cleaned):
        raise ValidationError(
            f"Неприпустиме ім'я інтерфейсу '{name}': очікується 1..16 символів (починається з літери)."
        )
    return cleaned


def validate_ipv4(ip: str) -> str:
    """Перевіряє коректність IPv4-адреси та повертає її в нормалізованому вигляді."""
    if not isinstance(ip, str):
        raise InvalidIPAddressError(str(ip), "адреса повинна бути рядком")

    cleaned = ip.strip()
    match = _IPV4_RE.match(cleaned)
    if not match:
        raise InvalidIPAddressError(ip)

    octets: list[str] = []
    for part in match.groups():
        value = int(part)
        if not 0 <= value <= 255:
            raise InvalidIPAddressError(ip, f"октет {value} виходить за межі 0..255")
        octets.append(str(value))

    return ".".join(octets)


def ip_to_int(ip: str) -> int:
    """Перетворює IPv4-адресу у 32-бітове беззнакове ціле число."""
    normalized = validate_ipv4(ip)
    o1, o2, o3, o4 = (int(part) for part in normalized.split("."))
    return (o1 << 24) | (o2 << 16) | (o3 << 8) | o4


def int_to_ip(value: int) -> str:
    """Перетворює 32-бітове ціле число назад у рядок IPv4."""
    if not 0 <= value <= 0xFFFFFFFF:
        raise ValueError("Число виходить за межі 32-бітового простору IPv4.")
    return ".".join(
        str((value >> shift) & 0xFF) for shift in (24, 16, 8, 0)
    )


def normalize_prefix(mask_or_prefix: str | int) -> int:
    """
    Приймає префікс CIDR (24, '/24') або маску ('255.255.255.0')
    та повертає цілочисельний префікс 0..32.
    """
    if isinstance(mask_or_prefix, bool):
        raise InvalidMaskError(str(mask_or_prefix))

    if isinstance(mask_or_prefix, int):
        if 0 <= mask_or_prefix <= 32:
            return mask_or_prefix
        raise InvalidMaskError(mask_or_prefix)

    if not isinstance(mask_or_prefix, str):
        raise InvalidMaskError(str(mask_or_prefix))

    cleaned = mask_or_prefix.strip()
    cidr_match = _CIDR_RE.match(cleaned)
    if cidr_match:
        prefix = int(cidr_match.group(1))
        if 0 <= prefix <= 32:
            return prefix
        raise InvalidMaskError(mask_or_prefix)

    # Перевірка формату десяткової маски (наприклад, 255.255.255.0)
    try:
        mask_int = ip_to_int(cleaned)
    except InvalidIPAddressError as exc:
        raise InvalidMaskError(mask_or_prefix) from exc

    # Перевірка безперервності одиничних бітів маски: інверсія + 1 має бути степенем двійки
    inverted = (~mask_int) & 0xFFFFFFFF
    if (inverted & (inverted + 1)) != 0:
        raise InvalidMaskError(mask_or_prefix, "одиничні біти маски не є неперервними")

    return mask_int.bit_count()


def prefix_to_netmask(prefix: int) -> str:
    """Перетворює префікс (0..32) у десяткову маску підмережі."""
    valid_prefix = normalize_prefix(prefix)
    mask_int = (0xFFFFFFFF << (32 - valid_prefix)) & 0xFFFFFFFF if valid_prefix > 0 else 0
    return int_to_ip(mask_int)


def get_network_address(ip: str, prefix: int) -> str:
    """Обчислює адресу мережі за допомогою побітового AND з маскою."""
    valid_prefix = normalize_prefix(prefix)
    mask_int = (0xFFFFFFFF << (32 - valid_prefix)) & 0xFFFFFFFF if valid_prefix > 0 else 0
    return int_to_ip(ip_to_int(ip) & mask_int)


def is_ip_in_subnet(ip: str, subnet_ip: str, prefix: int) -> bool:
    """Перевіряє, чи належить IP-адреса заданій підмережі."""
    valid_prefix = normalize_prefix(prefix)
    mask_int = (0xFFFFFFFF << (32 - valid_prefix)) & 0xFFFFFFFF if valid_prefix > 0 else 0
    return (ip_to_int(ip) & mask_int) == (ip_to_int(subnet_ip) & mask_int)


def validate_mac(mac: str) -> str:
    """Валідує MAC-адресу та нормалізує її до формату AA:BB:CC:DD:EE:FF."""
    if not isinstance(mac, str):
        raise InvalidMACError(str(mac))
    cleaned = mac.strip()
    if not _MAC_RE.match(cleaned):
        raise InvalidMACError(mac)
    return cleaned.replace("-", ":").upper()


def validate_vlan(vlan_id: int | str) -> int:
    """Перевіряє коректність ідентифікатора VLAN (1..4094)."""
    if isinstance(vlan_id, bool):
        raise InvalidVLANError(int(vlan_id))
    try:
        value = int(vlan_id)
    except (TypeError, ValueError) as exc:
        raise InvalidVLANError(-1) from exc

    if not 1 <= value <= 4094:
        raise InvalidVLANError(value)
    return value