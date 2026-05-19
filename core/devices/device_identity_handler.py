"""
DeviceIdentityHandler — extracts basic Device Serial Number / Hardware Version / Identity support behind the FeatureHandler interface (TASK-009 009.24).

This is the fifteenth feature extraction. Device Serial / Hardware Version is a simple, read-only, cross-device identity feature (distinct from the Device Name feature extracted in 009.15/009.23).

For this micro-chunk the handler is read-only (per scope).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional

from core.logi_device import FeatureHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class DeviceIdentityHandler(FeatureHandler):
    """Host-side Device Serial Number / Hardware Version / Identity read (read-only). Temporary (lost on reconnect/host switch)."""

    # 009.10/009.11: use the reusable default is_supported() from the base
    _feature_index_attr = "_device_identity_idx"

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device)
        self._listener = listener
        self.listener = listener

    # (is_supported() inherited from FeatureHandler base)

    def handle_read(self) -> Optional[List[int]]:
        """Return current device identity values (raw parameters) or None."""
        if not self.is_supported():
            return None
        if hasattr(self._listener, "read_device_identity"):
            return self._listener.read_device_identity()
        return None

    def handle_write(self, *args, **kwargs) -> bool:
        """Write not supported for this read-only feature in this micro-chunk."""
        return False
