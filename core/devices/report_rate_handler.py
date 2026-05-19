"""
ReportRateHandler — extracts Report Rate (read and set) behind the FeatureHandler interface (TASK-009 009.5).

This is the fifth feature extraction. Report Rate is a good candidate because it is a relatively clean, self-contained feature present across many Logitech gaming devices.

The handler owns the core read/write logic. Higher-level orchestration (if any) remains in Engine for this micro-chunk.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from core.logi_device import FeatureHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class ReportRateHandler(FeatureHandler):
    """Report Rate read/set handling for devices that support 0x8060."""

    # 009.10: use the reusable default is_supported() from the base
    _feature_index_attr = "_report_rate_idx"

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device)
        self._listener = listener
        # Also expose listener for the default is_supported() implementation
        self.listener = listener

    # (is_supported() now inherited from FeatureHandler base — no override needed)

    def handle_read(self) -> Optional[int]:
        """Read current report rate from the device, or None on failure."""
        if not self.is_supported() or self._listener._dev is None:
            return None
        # Delegate to the listener's existing implementation (keeps change minimal)
        return self._listener.read_report_rate() if hasattr(self._listener, "read_report_rate") else None

    def handle_write(self, rate: int) -> bool:
        """Set report rate. Returns success."""
        if not self.is_supported() or self._listener._dev is None:
            return False
        return self._listener.set_report_rate(rate) if hasattr(self._listener, "set_report_rate") else False
