"""
DeviceNameHandler — extracts basic Device Name / Friendly Name support behind the FeatureHandler interface (TASK-009 009.15).

This is the seventh feature extraction. Device Name (feature 0x0005) is a common, relatively isolated identity feature.

For this micro-chunk the handler is read-only (write is only implemented if the listener already supports it cleanly; currently it does not, so write will be a no-op stub).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from core.logi_device import FeatureHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class DeviceNameHandler(FeatureHandler):
    """Device Name / Friendly Name read support (write only if listener supports it cleanly)."""

    # 009.10/009.11: use the reusable default is_supported() from the base
    _feature_index_attr = "_device_name_idx"

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device)
        self._listener = listener
        self.listener = listener

    # (is_supported() inherited from FeatureHandler base)

    def handle_read(self) -> Optional[str]:
        """Return the current device/friendly name or None."""
        if not self.is_supported():
            return None
        if hasattr(self._listener, "read_device_name"):
            return self._listener.read_device_name()
        return None

    def handle_write(self, name: str) -> bool:
        """Set device name. Currently a no-op stub (listener write support not present in this micro-chunk)."""
        # Per scope: only implement write if the listener already supports it cleanly.
        # For 009.15 we keep the handler read-only / stub for write.
        print("[DeviceNameHandler] Write not supported in this micro-chunk (listener does not expose clean name write yet).")
        return False
