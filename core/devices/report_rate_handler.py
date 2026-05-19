"""
ReportRateHandler — extracts Report Rate (read and set) behind the FeatureHandler interface (TASK-009 009.5).

This is the fifth feature extraction. Report Rate is a good candidate because it is a relatively clean, self-contained feature present across many Logitech gaming devices.

The handler owns the core read/write logic. Higher-level orchestration (if any) remains in Engine for this micro-chunk.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from core.logi_device import FeatureHandler, ThinDelegationHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class ReportRateHandler(ThinDelegationHandler):
    """Report Rate read/set handling for devices that support 0x8060.

    009.12/009.25: Inherits from ThinDelegationHandler (which builds on
    SimpleDelegationHandler) for minimal-boilerplate delegation.
    """

    _feature_index_attr = "_report_rate_idx"
    _read_method_name = "read_report_rate"
    _write_method_name = "set_report_rate"

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device)
        self._listener = listener
        self.listener = listener

    # All behavior (is_supported, handle_read, handle_write) comes from ThinDelegationHandler / SimpleDelegationHandler
