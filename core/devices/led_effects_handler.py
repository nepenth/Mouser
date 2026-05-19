"""
LEDEffectsHandler — extracts basic LED Effects (patterns/modes beyond basic on/off + brightness) behind the FeatureHandler interface (TASK-009 009.19).

This is the eleventh feature extraction. LED Effects is a write-heavy, stateful feature distinct from the basic LED control extracted in 009.16.

For this micro-chunk we implement core effect read + write with optional parameters only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional, Tuple

from core.logi_device import FeatureHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class LEDEffectsHandler(FeatureHandler):
    """Host-side LED Effects read/write (patterns/modes beyond basic on/off + brightness). Temporary (lost on reconnect/host switch)."""

    # 009.10/009.11: use the reusable default is_supported() from the base
    _feature_index_attr = "_led_effects_idx"

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device)
        self._listener = listener
        self.listener = listener

    # (is_supported() inherited from FeatureHandler base)

    def handle_read(self) -> Optional[List[int]]:
        """Return current LED effect state/parameters (list of ints) or None."""
        if not self.is_supported():
            return None
        if hasattr(self._listener, "read_led_effect"):
            return self._listener.read_led_effect()
        return None

    def handle_write(self, effect: int, params: List[int] | None = None) -> bool:
        """Set LED effect and optional parameters. Returns success."""
        if not self.is_supported():
            return False
        if hasattr(self._listener, "set_led_effect"):
            return self._listener.set_led_effect(effect, params)
        return False
