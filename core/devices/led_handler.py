"""
LEDHandler — extracts basic mouse LED control (on/off + brightness) behind the FeatureHandler interface (TASK-009 009.16).

This is the eighth feature extraction. Many Logitech mice have internal LEDs controllable via HID++ (distinct from the external Litra illumination).

For this micro-chunk we implement core on/off + brightness only (no complex effects, zones, or color).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Tuple

from core.logi_device import FeatureHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class LEDHandler(FeatureHandler):
    """Host-side mouse LED on/off + brightness control. Temporary (lost on reconnect/host switch)."""

    # 009.10/009.11: use the reusable default is_supported() from the base
    _feature_index_attr = "_led_control_idx"

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device)
        self._listener = listener
        self.listener = listener

    # (is_supported() inherited from FeatureHandler base)

    def handle_read(self) -> Tuple[bool | None, int | None]:
        """Return (enabled, brightness) or (None, None)."""
        if not self.is_supported():
            return None, None
        if hasattr(self._listener, "read_led_state"):
            return self._listener.read_led_state()
        return None, None

    def handle_write(self, enabled: bool, brightness: int | None = None) -> bool:
        """Set LED on/off + optional brightness (0-100). Returns success."""
        if not self.is_supported():
            return False
        if hasattr(self._listener, "set_led_state"):
            lvl = None if brightness is None or brightness < 0 else brightness
            return self._listener.set_led_state(enabled, lvl)
        return False
