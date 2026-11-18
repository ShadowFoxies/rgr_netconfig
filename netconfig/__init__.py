"""Пакет автоматизованого конфігурування мережевих інтерфейсів та статичної маршрутизації."""

from .exceptions import (
    NetConfigError,
    ValidationError,
    InvalidIPAddressError,
    InvalidMaskError,
    InvalidMACError,
    InvalidVLANError,
    RoutingError,
    UnreachableGatewayError,
    DuplicateEntityError,
    StorageError,
)
from .manager import RouterConfigurator
from .models import (
    NetworkEntity,
    NetworkInterface,
    VlanInterface,
    StaticRoute,
)
from .storage import (
    load_text_config,
    save_to_json,
    load_from_json,
    save_to_csv,
    save_script,
)
from .validators import (
    normalize_interface_name,
    validate_ipv4,
    ip_to_int,
    int_to_ip,
    normalize_prefix,
    prefix_to_netmask,
    get_network_address,
    is_ip_in_subnet,
    validate_mac,
    validate_vlan,
)

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
    "RouterConfigurator",
    "NetworkEntity",
    "NetworkInterface",
    "VlanInterface",
    "StaticRoute",
    "load_text_config",
    "save_to_json",
    "load_from_json",
    "save_to_csv",
    "save_script",
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