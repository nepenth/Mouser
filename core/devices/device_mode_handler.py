"""
DeviceModeHandler — extracts basic Device Mode / Wireless Mode support behind the FeatureHandler interface (TASK-009 009.17).

This is the ninth feature extraction. Device Mode is a reasonably isolated, stateful capability present on many Logitech devices.

For this micro-chunk we implement core read + write of the mode value only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from core.logi_device import FeatureHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class DeviceModeHandler(FeatureHandler):
    """Host-side Device Mode / Wireless Mode read/write. Temporary (lost on reconnect/host switch)."""

    # 009.10/009.11: use the reusable default is_supported() from the base
    _feature_index_attr = "_device_mode_idx"

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device)
        self._listener = listener
        self.listener = listener

    # (is_supported() inherited from FeatureHandler base)

    def handle_read(self) -> Optional[int]:
        """Return current device mode value or None."""
        if not self.is_supported():
            return None
        if hasattr(self._listener, "read_device_mode"):
            return self._listener.read_device_mode()
        return None

    def handle_write(self, mode_value: int) -> bool:
        """Set device mode. Returns success."""
        if not self.is_supported():
            return False
        if hasattr(self._listener, "set_device_mode"):
            return self._listener.set_device_mode(mode_value)
        return False
