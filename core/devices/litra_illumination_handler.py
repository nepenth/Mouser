"""
Concrete FeatureHandler for Litra Beam illumination (TASK-009 009.1).

This is the first small feature extracted behind the new handler pattern.
The public Engine API remains 100% unchanged and backward-compatible.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Tuple

from core.logi_device import FeatureHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class LitraIlluminationHandler(FeatureHandler):
    """Host-side illumination control for Litra Beam devices.

    All changes are temporary (lost on reconnect or host switch).
    """

    # 009.11: use the reusable default is_supported() from the base
    _feature_index_attr = "_litra_illumination_idx"

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device)
        self._listener = listener  # the existing HidGestureListener (for now)
        # Also expose listener for the default is_supported() implementation
        self.listener = listener

    # (is_supported() now inherited from FeatureHandler base — no override needed)

    def handle_read(self) -> Tuple[bool | None, int | None]:
        """Return (enabled, brightness) or (None, None)."""
        if not self.is_supported():
            return None, None
        # Delegate to the existing listener method (full backward compatibility)
        return self._listener.read_litra_illumination()

    def handle_write(self, enabled: bool, brightness: int | None = None) -> bool:
        """Set illumination. Returns success."""
        if not self.is_supported():
            return False
        return self._listener.set_litra_illumination(enabled, brightness)
