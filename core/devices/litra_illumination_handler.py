"""
Concrete FeatureHandler for Litra Beam illumination (TASK-009 009.1).

This is the first small feature extracted behind the new handler pattern.
The public Engine API remains 100% unchanged and backward-compatible.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Tuple

from core.logi_device import FeatureHandler, ThinDelegationHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class LitraIlluminationHandler(ThinDelegationHandler):
    """Host-side illumination control for Litra Beam devices.

    All changes are temporary (lost on reconnect or host switch).

    009.25/009.27/009.28: Uses ThinDelegationHandler + the declarative helper.
    The custom handle_read/handle_write are intentionally kept.
    """

    _friendly_name = "Litra Illumination"  # 009.43: friendly display name for logging/debug/future UI

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device)
        self._listener = listener
        self.listener = listener
        # 009.27/009.28: single-line declarative style
        self._declare_attributes(
            feature_index_attr="_litra_illumination_idx",
            read_method="read_litra_illumination",
            write_method="set_litra_illumination"
        )

    # Custom handle_read/handle_write retained (different return shape).

    # 009.48 demonstration: example success-path logging using the new helper (for debug/traceability)
    # (In a real success path after a successful write, one could log self._get_success_label("set"))
        if not self.is_supported():
            return None, None
        # Delegate to the existing listener method (full backward compatibility)
        return self._listener.read_litra_illumination()

    def handle_write(self, enabled: bool, brightness: int | None = None) -> bool:
        """Set illumination. Returns success."""
        if not self.is_supported():
            return False
        return self._listener.set_litra_illumination(enabled, brightness)
