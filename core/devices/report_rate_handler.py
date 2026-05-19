"""
ReportRateHandler — extracts Report Rate (read and set) behind the FeatureHandler interface (TASK-009 009.5).

This is the fifth feature extraction. Report Rate is a good candidate because it is a relatively clean, self-contained feature present across many Logitech gaming devices.

The handler owns the core read/write logic. Higher-level orchestration (if any) remains in Engine for this micro-chunk.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from core.logi_device import FeatureHandler, SimpleDelegationHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class ReportRateHandler(SimpleDelegationHandler):
    """Report Rate read/set handling for devices that support 0x8060.

    009.12: Now inherits from SimpleDelegationHandler for default read/write forwarding.
    """

    # 009.10: use the reusable default is_supported() from the base
    _feature_index_attr = "_report_rate_idx"

    # 009.12: declare the listener method names for the SimpleDelegationHandler defaults
    _read_method_name = "read_report_rate"
    _write_method_name = "set_report_rate"

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device)
        self._listener = listener
        # Also expose listener for the default is_supported() implementation and delegation
        self.listener = listener

    # (is_supported() inherited from FeatureHandler base)
    # (handle_read / handle_write inherited from SimpleDelegationHandler)
