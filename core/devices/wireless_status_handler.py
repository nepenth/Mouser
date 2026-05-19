"""
WirelessStatusHandler — extracts basic Wireless Status (link quality / RSSI) support behind the FeatureHandler interface (TASK-009 009.22).

This is the fourteenth feature extraction. Wireless Status is a reasonably isolated, read-only, wireless-specific status feature present on many wireless Logitech devices (distinct from Wireless Power in 009.18 and Wireless Channel in 009.20).

For this micro-chunk the handler is read-only (per scope).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional

from core.logi_device import FeatureHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class WirelessStatusHandler(FeatureHandler):
    """Host-side Wireless Status (link quality / RSSI) read. Temporary (lost on reconnect/host switch)."""

    # 009.10/009.11: use the reusable default is_supported() from the base
    _feature_index_attr = "_wireless_status_idx"

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device)
        self._listener = listener
        self.listener = listener

    # (is_supported() inherited from FeatureHandler base)

    def handle_read(self) -> Optional[List[int]]:
        """Return current wireless status values (raw parameters) or None."""
        if not self.is_supported():
            return None
        if hasattr(self._listener, "read_wireless_status"):
            return self._listener.read_wireless_status()
        return None

    def handle_write(self, *args, **kwargs) -> bool:
        """Write not supported for this read-only feature in this micro-chunk."""
        return False
