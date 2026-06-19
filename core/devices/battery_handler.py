"""
BatteryHandler — extracts battery read/result handling behind the FeatureHandler interface (TASK-009 009.2).

This is the second feature extraction after Litra illumination. The goal is to exercise
the handler model on a more established, cross-device feature (battery exists on many
mice and some keyboards) while keeping every public API and all existing behavior 100%
unchanged.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from core.logi_device import DefaultThinHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class BatteryHandler(DefaultThinHandler):
    """Battery read handling for devices that support UNIFIED_BATTERY or the older battery feature.

    009.25/009.26/009.30: Uses DefaultThinHandler.
    Intentionally delegates to ``HidGestureListener.read_battery()`` (listener-owned
    pending-state machine + ``_parse_battery_response``). No duplicate HID++ logic here.
    """

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device, listener,
                         feature_index_attr="_battery_idx",
                         read_method="read_battery")
        self._listener = listener

    # All behavior (is_supported, handle_read) comes from DefaultThinHandler.
    # handle_read forwards to listener.read_battery() which returns int 0-100 or None.