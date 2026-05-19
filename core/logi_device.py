"""
Minimal skeleton for the cleaner LogitechDevice + FeatureHandler architecture (TASK-009).

This is the first tiny, low-risk extraction step. The goal is to prove the pattern
works while keeping 100% backward compatibility with all existing mouse, keyboard,
and light behavior.

Only one feature (Litra illumination) is extracted in this initial micro-chunk.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class FeatureHandler:
    """Base class for a single HID++ feature handler.

    Concrete handlers implement the actual read/write logic for one feature
    (e.g., Litra illumination, Battery, SmartShift, etc.).
    """

    def __init__(self, device: "LogitechDevice"):
        self.device = device

    def is_supported(self) -> bool:
        """Return True if this feature is present on the device."""
        raise NotImplementedError

    def handle_read(self, *args, **kwargs) -> Any:
        """Perform a read operation for this feature."""
        raise NotImplementedError

    def handle_write(self, *args, **kwargs) -> Any:
        """Perform a write operation for this feature."""
        raise NotImplementedError


class LogitechDevice:
    """Very lightweight base for a Logitech HID++ device.

    Over time this will hold identity, a collection of FeatureHandlers,
    per-device state, etc. For now it is deliberately minimal.
    """

    def __init__(self, product_id: int, name: str = "", key: Optional[str] = None):
        self.product_id = product_id
        self.name = name
        self.key = key or str(product_id)
        self._handlers: Dict[str, FeatureHandler] = {}

    def add_handler(self, name: str, handler: FeatureHandler) -> None:
        self._handlers[name] = handler

    def get_handler(self, name: str) -> Optional[FeatureHandler]:
        return self._handlers.get(name)

    def has_handler(self, name: str) -> bool:
        return name in self._handlers
