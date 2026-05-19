"""
DeviceIdentityHandler — extracts basic Device Serial Number / Hardware Version / Identity support behind the FeatureHandler interface (TASK-009 009.24).

This is the fifteenth feature extraction. Device Serial / Hardware Version is a simple, read-only, cross-device identity feature (distinct from the Device Name feature extracted in 009.15/009.23).

For this micro-chunk the handler is read-only (per scope).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional

from core.logi_device import FeatureHandler, ThinDelegationHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class DeviceIdentityHandler(ThinDelegationHandler):
    """Host-side Device Serial Number / Hardware Version / Identity read (read-only). Temporary (lost on reconnect/host switch)."""

    # 009.10/009.11: use the reusable default is_supported() from the base
    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device)
        self._listener = listener
        self.listener = listener
        # 009.27/009.28: single-line declarative style (read-only)
        self._declare_attributes(
            feature_index_attr="_device_identity_idx",
            read_method="read_device_identity"
        )

    # All behavior (is_supported + handle_read) comes from ThinDelegationHandler.
    # handle_write remains a no-op because this feature is read-only.
    def handle_write(self, *args, **kwargs) -> bool:
        return False
