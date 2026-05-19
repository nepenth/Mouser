"""
DeviceTypeHandler — extracts basic Device Type / Product Type support behind the FeatureHandler interface (TASK-009 009.35).

This is the seventeenth feature extraction. Device Type / Product Type is a simple, read-only, cross-device identity feature (complementing Device Name, Device Identity, and Device Friendly Name).

For this micro-chunk the handler is read-only (per scope).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from core.logi_device import FeatureHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class DeviceTypeHandler(FeatureHandler):
    """Host-side Device Type / Product Type read (read-only). Temporary (lost on reconnect/host switch)."""

    # 009.10/009.11: use the reusable default is_supported() from the base
    _feature_index_attr = "_device_type_idx"

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device)
        self._listener = listener
        self.listener = listener

    # (is_supported() inherited from FeatureHandler base)

    def handle_read(self) -> Optional[int]:
        """Return current device type / product type value or None."""
        if not self.is_supported():
            return None
        if hasattr(self._listener, "read_device_type"):
            return self._listener.read_device_type()
        return None

    def handle_write(self, *args, **kwargs) -> bool:
        """Write not supported for this read-only feature in this micro-chunk."""
        return False
