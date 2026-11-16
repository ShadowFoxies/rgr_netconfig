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