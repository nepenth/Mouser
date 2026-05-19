"""
WirelessPowerHandler — extracts basic Wireless Power / RF Power Management support behind the FeatureHandler interface (TASK-009 009.18).

This is the tenth feature extraction. Wireless Power is a reasonably isolated, stateful capability present on many wireless Logitech devices (distinct from Battery).

For this micro-chunk we implement core read + write of the power level/mode only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from core.logi_device import FeatureHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class WirelessPowerHandler(FeatureHandler):
    """Host-side Wireless Power / RF Power read/write. Temporary (lost on reconnect/host switch)."""

    # 009.10/009.11: use the reusable default is_supported() from the base
    _feature_index_attr = "_wireless_power_idx"

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device)
        self._listener = listener
        self.listener = listener

    # (is_supported() inherited from FeatureHandler base)

    def handle_read(self) -> Optional[int]:
        """Return current wireless power level/mode or None."""
        if not self.is_supported():
            return None
        if hasattr(self._listener, "read_wireless_power"):
            return self._listener.read_wireless_power()
        return None

    def handle_write(self, power_value: int) -> bool:
        """Set wireless power level/mode. Returns success."""
        if not self.is_supported():
            return False
        if hasattr(self._listener, "set_wireless_power"):
            return self._listener.set_wireless_power(power_value)
        return False
