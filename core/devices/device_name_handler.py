"""
DeviceNameHandler — extracts basic Device Name / Friendly Name support behind the FeatureHandler interface (TASK-009 009.15).

This is the seventh feature extraction. Device Name (feature 0x0005) is a common, relatively isolated identity feature.

Supports read and write for device name / friendly name via the listener's 0x0005 path.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from core.logi_device import FeatureHandler, ThinDelegationHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class DeviceNameHandler(ThinDelegationHandler):
    """Device Name / Friendly Name read support (write only if listener supports it cleanly)."""

    # 009.10/009.11: use the reusable default is_supported() from the base
    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device)
        self._listener = listener
        self.listener = listener
        # 009.27/009.28: single-line declarative style (read + write)
        self._declare_attributes(
            feature_index_attr="_device_name_idx",
            read_method="read_device_name",
            write_method="set_device_name"
        )

    # All behavior (is_supported + handle_read + handle_write) comes from ThinDelegationHandler / DefaultThinHandler.

    # 009.31: Friendly Name (user-settable) aliases — delegate to the existing name methods (same underlying feature on most devices)
    def handle_read_friendly_name(self) -> Optional[str]:
        if hasattr(self._listener, "read_device_friendly_name"):
            return self._listener.read_device_friendly_name()
        return self.handle_read()

    def handle_write_friendly_name(self, name: str) -> bool:
        if hasattr(self._listener, "set_device_friendly_name"):
            return self._listener.set_device_friendly_name(name)
        return self.handle_write(name)
