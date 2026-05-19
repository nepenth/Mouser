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

    009.25/009.26/009.27: Uses ThinDelegationHandler + the declarative helper
    for the most concise possible thin-handler declaration.
    """

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device)
        self._listener = listener
        self.listener = listener
        # 009.27: single-line declarative style for the three standard attributes
        self._declare_attributes(
            feature_index_attr="_onboard_profiles_idx",
            read_method="read_onboard_profile",
            write_method="switch_onboard_profile"
        )

    # All behavior (is_supported + handle_read + handle_write) comes from ThinDelegationHandler.
