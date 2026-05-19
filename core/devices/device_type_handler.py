"""
DeviceTypeHandler — extracts basic Device Type / Product Type support behind the FeatureHandler interface (TASK-009 009.35).

This is the seventeenth feature extraction. Device Type / Product Type is a simple, read-only, cross-device identity feature (complementing Device Name, Device Identity, and Device Friendly Name).

For this micro-chunk the handler is read-only (per scope).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from core.logi_device import FeatureHandler, UltraThinHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class DeviceTypeHandler(UltraThinHandler):
    """Host-side Device Type / Product Type read (read-only). Temporary (lost on reconnect/host switch).

    009.35/009.38: Uses UltraThinHandler (the ultra-light base for the absolute simplest pure thin cases).
    """

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device, listener,
                         feature_index_attr="_device_type_idx",
                         read_method="read_device_type")
        self._listener = listener
        self._mark_as_read_only()

    # All behavior (is_supported + handle_read) comes from UltraThinHandler / RecommendedThinHandler.
    # handle_write remains a no-op (read-only feature).
