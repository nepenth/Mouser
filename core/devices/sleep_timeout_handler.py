"""
SleepTimeoutHandler — extracts basic Sleep Timeout / Power Save Timeout support behind the FeatureHandler interface (TASK-009 009.21).

This is the thirteenth feature extraction. Sleep Timeout is a reasonably isolated, stateful setting present on many Logitech devices.

For this micro-chunk we implement core read + write of the timeout value only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from core.logi_device import FeatureHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class SleepTimeoutHandler(FeatureHandler):
    """Host-side Sleep Timeout / Power Save Timeout read/write. Temporary (lost on reconnect/host switch)."""

    # 009.10/009.11: use the reusable default is_supported() from the base
    _feature_index_attr = "_sleep_timeout_idx"

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device)
        self._listener = listener
        self.listener = listener

    # (is_supported() inherited from FeatureHandler base)

    def handle_read(self) -> Optional[int]:
        """Return current sleep/power-save timeout value or None."""
        if not self.is_supported():
            return None
        if hasattr(self._listener, "read_sleep_timeout"):
            return self._listener.read_sleep_timeout()
        return None

    def handle_write(self, timeout_value: int) -> bool:
        """Set sleep/power-save timeout. Returns success."""
        if not self.is_supported():
            return False
        if hasattr(self._listener, "set_sleep_timeout"):
            return self._listener.set_sleep_timeout(timeout_value)
        return False
