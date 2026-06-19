"""
FnInversionHandler — extracts K375S FN inversion read/set behind the FeatureHandler interface (TASK-004 004.5).

Keyboard middle-path feature. The handler owns thin delegation to the listener;
per-device policy and host-state persistence remain in Engine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from core.logi_device import DefaultThinHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class FnInversionHandler(DefaultThinHandler):
    """K375S FN inversion read/set handling for devices that support 0x40A3."""

    _friendly_name = "FN Inversion"

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device, listener,
                         feature_index_attr="_fn_inversion_idx",
                         read_method="read_fn_inversion",
                         write_method="set_fn_inversion")
        self._listener = listener

    # All behavior (is_supported, handle_read, handle_write) comes from DefaultThinHandler.