"""
RemainingPairingHandler — extracts the Remaining Pairing slots count behind the FeatureHandler interface (TASK-009 009.49, fresh non-duplicate micro-chunk).

This is a tiny, isolated, read-only feature that reports how many more devices can be paired to the receiver. It is useful for UI ("you can pair X more devices") and has not been exposed as a dedicated handler before.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from core.logi_device import FeatureHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class RemainingPairingHandler(FeatureHandler):
    """Host-side Remaining Pairing slots read (read-only)."""

    _feature_index_attr = "_remaining_pairing_idx"

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device)
        self._listener = listener
        self.listener = listener

    def handle_read(self) -> Optional[int]:
        """Return the number of remaining pairing slots, or None."""
        if not self.is_supported():
            return None
        if hasattr(self._listener, "get_remaining_pairing_slots"):
            return self._listener.get_remaining_pairing_slots()
        return None

    def handle_write(self, *args, **kwargs) -> bool:
        """Write not supported (read-only feature)."""
        return False
