"""
OnboardProfilesHandler — extracts basic onboard profile read/switch behind the FeatureHandler interface (TASK-009 009.9).

This is the sixth feature extraction. Onboard Profiles (0x8100) is a significant, commonly discussed capability on gaming mice (G502 X family, etc.).

The handler owns the core “get current profile” and “switch profile” logic for this micro-chunk. Higher-level profile management (loading/saving from config, profile list handling) remains in Engine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from core.logi_device import FeatureHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class OnboardProfilesHandler(FeatureHandler):
    """Basic onboard profile read/switch handling for devices that support 0x8100."""

    # 009.11: use the reusable default is_supported() from the base
    _feature_index_attr = "_onboard_profiles_idx"

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device)
        self._listener = listener
        # Also expose listener for the default is_supported() implementation
        self.listener = listener

    # (is_supported() now inherited from FeatureHandler base — no override needed)

    def handle_read(self) -> Optional[int]:
        """Return the current onboard profile index (or None)."""
        if not self.is_supported() or self._listener._dev is None:
            return None
        # Delegate to the listener's existing implementation (keeps change minimal)
        if hasattr(self._listener, "read_onboard_profile"):
            return self._listener.read_onboard_profile()
        return None

    def handle_write(self, profile_index: int) -> bool:
        """Switch to the given onboard profile index. Returns success."""
        if not self.is_supported() or self._listener._dev is None:
            return False
        if hasattr(self._listener, "switch_onboard_profile"):
            return self._listener.switch_onboard_profile(profile_index)
        return False
