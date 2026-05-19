"""
OnboardProfilesHandler — extracts basic onboard profile read/switch behind the FeatureHandler interface (TASK-009 009.9).

This is the sixth feature extraction. Onboard Profiles (0x8100) is a significant, commonly discussed capability on gaming mice (G502 X family, etc.).

The handler owns the core “get current profile” and “switch profile” logic for this micro-chunk. Higher-level profile management (loading/saving from config, profile list handling) remains in Engine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from core.logi_device import FeatureHandler, SimpleDelegationHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class OnboardProfilesHandler(SimpleDelegationHandler):
    """Basic onboard profile read/switch handling for devices that support 0x8100."""

    # 009.10/009.11: use the reusable default is_supported() from the base
    _feature_index_attr = "_onboard_profiles_idx"

    # 009.13: declare the listener method names for the SimpleDelegationHandler defaults
    _read_method_name = "read_onboard_profile"
    _write_method_name = "switch_onboard_profile"

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device)
        self._listener = listener
        # Also expose listener for the default is_supported() implementation and delegation
        self.listener = listener

    # (is_supported() inherited from FeatureHandler base)
    # (handle_read / handle_write inherited from SimpleDelegationHandler)
