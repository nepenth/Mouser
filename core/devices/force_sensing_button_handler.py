"""
ForceSensingButtonHandler — extracts basic Force Sensing Button support behind the FeatureHandler interface (TASK-009 009.51, fresh non-duplicate micro-chunk).

This is a small, isolated read-focused feature for pressure-sensitive buttons (distinct from standard REPROG buttons).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, List

from core.logi_device import FeatureHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class ForceSensingButtonHandler(FeatureHandler):
    """Host-side Force Sensing Button read (read-only for this micro-chunk)."""

    _feature_index_attr = "_force_sensing_button_idx"

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device)
        self._listener = listener
        self.listener = listener

    def handle_read(self) -> Optional[List[int]]:
        """Return force sensing button data (raw or structured) or None."""
        if not self.is_supported():
            return None
        if hasattr(self._listener, "get_force_sensing_buttons"):
            return self._listener.get_force_sensing_buttons()
        return None

    def handle_write(self, *args, **kwargs) -> bool:
        """Write not supported for this micro-chunk (read-focused)."""
        return False
