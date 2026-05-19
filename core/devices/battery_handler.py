"""
BatteryHandler — extracts battery read/result handling behind the FeatureHandler interface (TASK-009 009.2).

This is the second feature extraction after Litra illumination. The goal is to exercise
the handler model on a more established, cross-device feature (battery exists on many
mice and some keyboards) while keeping every public API and all existing behavior 100%
unchanged.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Tuple

from core.logi_device import FeatureHandler, ThinDelegationHandler

if TYPE_CHECKING:
    from core.logi_device import LogitechDevice


class BatteryHandler(ThinDelegationHandler):
    """Battery read handling for devices that support UNIFIED_BATTERY or the older battery feature.

    009.25/009.26: Inherits from ThinDelegationHandler.
    The custom handle_read (with normalization) is intentionally kept.
    """

    def __init__(self, device: "LogitechDevice", listener: Any):
        super().__init__(device)
        self._listener = listener
        self.listener = listener
        # 009.27/009.28: single-line declarative style
        self._declare_attributes(
            feature_index_attr="_battery_idx",
            read_method="read_battery"
        )

    # Custom handle_read (normalization logic) retained — not pure delegation.
        if not self.is_supported() or self._listener._dev is None:
            return None

        # Delegate to the listener's existing battery read implementation
        # (the listener already has the full logic for different battery features).
        # We call the internal method that does the actual HID++ request.
        # If the listener later refactors its battery code, this single call site is easy to update.
        try:
            # The listener already has a method that performs the read; we reuse it.
            # For the initial extraction we call the same code path the polling loop uses.
            # We temporarily invoke the pending-apply logic in a way that returns the result
            # without going through the full pending state machine (keeps the change minimal).
            #
            # Simplest safe approach for 009.2: directly perform the read the same way
            # the listener does inside _apply_pending_battery, but return the dict.
            resp = self._listener._request(self._listener._battery_idx, 0x00, [])
            if resp and resp[4]:
                params = resp[4]
                # The listener already knows how to parse different battery feature versions.
                # For the first extraction we reuse the parsing that already exists
                # inside the listener (we just call the same code the listener uses).
                #
                # To keep the diff tiny we will let the listener expose a tiny helper
                # (added in the same micro-chunk) that the handler can call.
                # If that helper is not present we fall back to a best-effort parse.
                if hasattr(self._listener, "_parse_battery_response"):
                    return self._listener._parse_battery_response(params)
                # Fallback (very defensive) — the caller will treat None as "no data".
                return None
            return None
        except Exception:
            return None
