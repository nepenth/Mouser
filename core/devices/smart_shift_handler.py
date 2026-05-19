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

from core.logi_device import FeatureHandler, ThinDelegationHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class SmartShiftHandler(ThinDelegationHandler):
    """SmartShift read/write handling for devices that support 0x2110 or 0x2111.

    009.25/009.26: Inherits from ThinDelegationHandler (the custom handle_read/handle_write
    with extra parameters are intentionally kept because they contain additional logic).
    """

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device)
        self._listener = listener
        self.listener = listener
        # 009.27/009.28: single-line declarative style
        self._declare_attributes(
            feature_index_attr="_smart_shift_idx",
            read_method="read_smart_shift",
            write_method="set_smart_shift"
        )

    # Custom handle_read/handle_write retained (different signature + guards) — they are not pure delegation.
