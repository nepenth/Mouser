"""
DPIHandler — extracts core DPI set/read logic behind the FeatureHandler interface (TASK-009 009.4).

This is the fourth feature extraction. DPI is an excellent candidate because:
- It is one of the most frequently used mouse features.
- It has both read and write paths.
- It interacts with presets and cycling logic (which we leave in Engine for this micro-chunk).

The handler owns the core set_dpi (including clamping) and read_dpi logic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from core.logi_device import FeatureHandler, DefaultThinHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class DPIHandler(DefaultThinHandler):
    """Core DPI set/read handling for devices that support ADJUSTABLE_DPI (0x2201).

    009.25/009.26/009.30: Uses DefaultThinHandler.
    The custom handle_write (clamping note) is intentionally kept.
    """

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device, listener,
                         feature_index_attr="_dpi_idx",
                         read_method="read_dpi",
                         write_method="set_dpi")
        self._listener = listener

    # Custom handle_write retained (per 009.4 scope comment).
        if not self.is_supported() or self._listener._dev is None:
            return False
        return self._listener.set_dpi(dpi_value)

    def handle_read(self) -> Optional[int]:
        """Read current DPI from the device, or None on failure."""
        if not self.is_supported() or self._listener._dev is None:
            return None
        # Delegate to the listener's existing DPI read implementation
        return self._listener.read_dpi() if hasattr(self._listener, "read_dpi") else None
