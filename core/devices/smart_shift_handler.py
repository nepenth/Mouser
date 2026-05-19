"""
SmartShiftHandler — extracts SmartShift (read, set, mode, enabled, threshold) behind the FeatureHandler interface (TASK-009 009.3).

This is the third feature extraction. SmartShift is a good stress-test because it has:
- Read + write paths
- Mode, enabled flag, and threshold parameters
- Both classic (0x2110) and enhanced (0x2111) variants

The handler owns the core read/write logic. The Engine's higher-level toggle/switch helpers and polling remain thin callers (minimal change).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

from core.logi_device import FeatureHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class SmartShiftHandler(FeatureHandler):
    """SmartShift read/write handling for devices that support 0x2110 or 0x2111."""

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device)
        self._listener = listener

    def is_supported(self) -> bool:
        return getattr(self._listener, "_smart_shift_idx", None) is not None

    def handle_read(self) -> Optional[Dict[str, Any]]:
        """Return the current SmartShift state dict or None."""
        if not self.is_supported() or self._listener._dev is None:
            return None
        # Delegate to the listener's existing read implementation (keeps change minimal)
        return self._listener.read_smart_shift()

    def handle_write(self, mode: str, smart_shift_enabled: bool = False, threshold: int = 25) -> bool:
        """Send SmartShift settings. Returns success."""
        if not self.is_supported() or self._listener._dev is None:
            return False
        return self._listener.set_smart_shift(mode, smart_shift_enabled, threshold)
