"""
OnboardProfilesHandler — extracts basic onboard profile read/switch behind the FeatureHandler interface (TASK-009 009.9).

This is the sixth feature extraction. Onboard Profiles (0x8100) is a significant, commonly discussed capability on gaming mice (G502 X family, etc.).

The handler owns the core “get current profile” and “switch profile” logic for this micro-chunk. Higher-level profile management (loading/saving from config, profile list handling) remains in Engine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from core.logi_device import FeatureHandler, ThinDelegationHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class OnboardProfilesHandler(ThinDelegationHandler):
    """Basic onboard profile read/switch handling for devices that support 0x8100.

    009.25/009.26: Inherits from ThinDelegationHandler (pure thin delegation case).
    """

    _feature_index_attr = "_onboard_profiles_idx"
    _read_method_name = "read_onboard_profile"
    _write_method_name = "switch_onboard_profile"

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device)
        self._listener = listener
        self.listener = listener

    # All behavior (is_supported + handle_read + handle_write) comes from ThinDelegationHandler.
