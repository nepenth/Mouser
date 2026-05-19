"""
WirelessStatusHandler — extracts basic Wireless Status (link quality / RSSI) support behind the FeatureHandler interface (TASK-009 009.22).

This is the fourteenth feature extraction. Wireless Status is a reasonably isolated, read-only, wireless-specific status feature present on many wireless Logitech devices (distinct from Wireless Power in 009.18 and Wireless Channel in 009.20).

For this micro-chunk the handler is read-only (per scope).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional

from core.logi_device import FeatureHandler, ThinDelegationHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class WirelessStatusHandler(ThinDelegationHandler):
    """Host-side Wireless Status (link quality / RSSI) read (read-only). Temporary (lost on reconnect/host switch).

    009.25: Migrated to ThinDelegationHandler for minimal boilerplate.
    """

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device)
        self._listener = listener
        self.listener = listener
        # 009.27/009.28: single-line declarative style (read-only)
        self._declare_attributes(
            feature_index_attr="_wireless_status_idx",
            read_method="read_wireless_status"
        )

    # All behavior (is_supported + handle_read) comes from ThinDelegationHandler.
    # We keep a minimal safe override for the read-only case.
    def handle_write(self, *args, **kwargs) -> bool:
        return False
