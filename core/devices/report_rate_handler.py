"""
ReportRateHandler — extracts Report Rate (read and set) behind the FeatureHandler interface (TASK-009 009.5).

This is the fifth feature extraction. Report Rate is a good candidate because it is a relatively clean, self-contained feature present across many Logitech gaming devices.

The handler owns the core read/write logic. Higher-level orchestration (if any) remains in Engine for this micro-chunk.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from core.logi_device import FeatureHandler, DefaultThinHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class ReportRateHandler(DefaultThinHandler):
    """Report Rate read/set handling for devices that support 0x8060.

    009.12/009.25/009.27/009.29: Uses DefaultThinHandler (the ultra-light
    convenience base that combines all the harvested patterns).
    """

    _friendly_name = "Report Rate"  # 009.43: friendly display name for logging/debug/future UI

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device, listener,
                         feature_index_attr="_report_rate_idx",
                         read_method="read_report_rate",
                         write_method="set_report_rate")
        self._listener = listener

    # All behavior (is_supported, handle_read, handle_write) comes from DefaultThinHandler / ThinDelegationHandler.

    # 009.48 demonstration: example success-path logging using the new helper (for debug/traceability)
    # (In a real success path after a successful read, one could log self._get_success_label("read"))
    # Example: print(self._get_success_label("read"))  # "Read Report Rate succeeded"
