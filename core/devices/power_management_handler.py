"""
PowerManagementHandler — extracts basic Power Management (beyond Sleep Timeout / Wireless Power) support behind the FeatureHandler interface (TASK-009 009.37).

This is the eighteenth feature extraction. Power Management (additional power save settings or profiles) is a reasonably isolated, stateful capability present on many Logitech devices (distinct from Battery, Wireless Power, and Sleep Timeout).

For this micro-chunk we implement core read + write of the power management settings only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional

from core.logi_device import FeatureHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class PowerManagementHandler(FeatureHandler):
    """Host-side Power Management (beyond Sleep Timeout / Wireless Power / Battery) read/write. Temporary (lost on reconnect/host switch).

    009.37 / 009.42 / 009.45: Extended to surface even more labeled fields (extra_setting_3, extra_setting_4, etc.) when the listener provides them.
    """

    # 009.10/009.11: use the reusable default is_supported() from the base
    _feature_index_attr = "_power_management_idx"

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device)
        self._listener = listener
        self.listener = listener

    # (is_supported() inherited from FeatureHandler base)

    def handle_read(self) -> Optional[dict]:
        """Return current power management settings / profile (raw + labeled fields when available) or None."""
        if not self.is_supported():
            return None
        if hasattr(self._listener, "read_power_management"):
            return self._listener.read_power_management()
        return None

    def handle_write(self, settings) -> bool:
        """Set power management settings / profile. Returns success."""
        if not self.is_supported():
            return False
        if hasattr(self._listener, "set_power_management"):
            return self._listener.set_power_management(settings)
        return False
