"""
WirelessChannelHandler — extracts basic Wireless Channel / RF Channel support behind the FeatureHandler interface (TASK-009 009.20).

This is the twelfth feature extraction. Wireless Channel is a reasonably isolated, stateful capability present on many wireless Logitech devices (distinct from Wireless Power in 009.18).

For this micro-chunk we implement core read + write of the channel value only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from core.logi_device import FeatureHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class WirelessChannelHandler(FeatureHandler):
    """Host-side Wireless Channel / RF Channel read/write. Temporary (lost on reconnect/host switch)."""

    # 009.10/009.11: use the reusable default is_supported() from the base
    _feature_index_attr = "_wireless_channel_idx"

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device)
        self._listener = listener
        self.listener = listener

    # (is_supported() inherited from FeatureHandler base)

    def handle_read(self) -> Optional[int]:
        """Return current wireless channel or None."""
        if not self.is_supported():
            return None
        if hasattr(self._listener, "read_wireless_channel"):
            return self._listener.read_wireless_channel()
        return None

    def handle_write(self, channel_value: int) -> bool:
        """Set wireless channel. Returns success."""
        if not self.is_supported():
            return False
        if hasattr(self._listener, "set_wireless_channel"):
            return self._listener.set_wireless_channel(channel_value)
        return False
