"""
BacklightHandler — extracts BACKLIGHT2 read/set behind the FeatureHandler interface (TASK-004 004.5).

Keyboard middle-path feature (MX Mechanical Mini etc.). The handler owns thin delegation
to the listener; per-device policy and host-state persistence remain in Engine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from core.logi_device import DefaultThinHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class BacklightHandler(DefaultThinHandler):
    """BACKLIGHT2 read/set handling for devices that support 0x1982."""

    _friendly_name = "Backlight"

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device, listener,
                         feature_index_attr="_backlight2_idx",
                         read_method="read_backlight",
                         write_method="set_backlight")
        self._listener = listener

    # All behavior (is_supported, handle_read, handle_write) comes from DefaultThinHandler.