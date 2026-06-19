"""
Engine — wires the mouse hook to the key simulator using the
current configuration.  Sits between the hook layer and the UI.
Supports per-application auto-switching of profiles.
"""

import threading
import time
from core.mouse_hook import MouseHook, MouseEvent
from core.key_simulator import (
    ACTIONS, execute_action, is_mouse_button_action,
    inject_mouse_down, inject_mouse_up,
)
from core.config import (
    load_config, get_active_mappings, get_profile_for_app,
    BUTTON_TO_EVENTS, GESTURE_DIRECTION_BUTTONS, save_config,
    get_keyboard_middle_path_settings,
    get_saved_keyboard_host_replay,
    save_keyboard_host_backlight_state,
    save_keyboard_host_fn_inversion_state,
)
from core.app_detector import AppDetector
from core.mouse_hook_types import HidRuntimeState
from core.linux_permissions import (
    linux_permission_log_message,
    linux_permission_report,
    linux_permission_status_message,
)
from core.logi_devices import clamp_dpi
from core.device_state import (
    active_mouse_device_from_connected,
    build_all_devices_list,
)

# 009.1/009.6: minimal LogitechDevice / FeatureHandler imports (only used when a handler is attached)
try:
    from core.logi_device import LogitechDevice, maybe_attach_handler
    from core.devices.litra_illumination_handler import LitraIlluminationHandler
except Exception:
    LogitechDevice = None
    LitraIlluminationHandler = None
    maybe_attach_handler = None

# 009.2: BatteryHandler import (guarded)
try:
    from core.devices.battery_handler import BatteryHandler
except Exception:
    BatteryHandler = None

# 009.3: SmartShiftHandler import (guarded)
try:
    from core.devices.smart_shift_handler import SmartShiftHandler
except Exception:
    SmartShiftHandler = None

# 009.4: DPIHandler import (guarded)
try:
    from core.devices.dpi_handler import DPIHandler
except Exception:
    DPIHandler = None

# 009.5: ReportRateHandler import (guarded)
try:
    from core.devices.report_rate_handler import ReportRateHandler
except Exception:
    ReportRateHandler = None

# 004.5: BacklightHandler / FnInversionHandler imports (guarded)
try:
    from core.devices.backlight_handler import BacklightHandler
except Exception:
    BacklightHandler = None

try:
    from core.devices.fn_inversion_handler import FnInversionHandler
except Exception:
    FnInversionHandler = None

# 009.9: OnboardProfilesHandler import (guarded)
try:
    from core.devices.onboard_profiles_handler import OnboardProfilesHandler
except Exception:
    OnboardProfilesHandler = None

# 009.15: DeviceNameHandler import (guarded)
try:
    from core.devices.device_name_handler import DeviceNameHandler
except Exception:
    DeviceNameHandler = None

# 009.16: LEDHandler import (guarded)
try:
    from core.devices.led_handler import LEDHandler
except Exception:
    LEDHandler = None

# 009.17: DeviceModeHandler import (guarded)
try:
    from core.devices.device_mode_handler import DeviceModeHandler
except Exception:
    DeviceModeHandler = None

# 009.18: WirelessPowerHandler import (guarded)
try:
    from core.devices.wireless_power_handler import WirelessPowerHandler
except Exception:
    WirelessPowerHandler = None

# 009.19: LEDEffectsHandler import (guarded)
try:
    from core.devices.led_effects_handler import LEDEffectsHandler
except Exception:
    LEDEffectsHandler = None

# 009.20: WirelessChannelHandler import (guarded)
try:
    from core.devices.wireless_channel_handler import WirelessChannelHandler
except Exception:
    WirelessChannelHandler = None

# 009.21: SleepTimeoutHandler import (guarded)
try:
    from core.devices.sleep_timeout_handler import SleepTimeoutHandler
except Exception:
    SleepTimeoutHandler = None

# 009.22: WirelessStatusHandler import (guarded)
try:
    from core.devices.wireless_status_handler import WirelessStatusHandler
except Exception:
    WirelessStatusHandler = None

# 009.24: DeviceIdentityHandler import (guarded)
try:
    from core.devices.device_identity_handler import DeviceIdentityHandler
except Exception:
    DeviceIdentityHandler = None

# 009.35: DeviceTypeHandler import (guarded)
try:
    from core.devices.device_type_handler import DeviceTypeHandler
except Exception:
    DeviceTypeHandler = None

# 009.49 (fresh): RemainingPairingHandler import (guarded)
try:
    from core.devices.remaining_pairing_handler import RemainingPairingHandler
except Exception:
    RemainingPairingHandler = None

# 009.51 (fresh): ForceSensingButtonHandler import (guarded)
try:
    from core.devices.force_sensing_button_handler import ForceSensingButtonHandler
except Exception:
    ForceSensingButtonHandler = None

# 009.37: PowerManagementHandler import (guarded)
try:
    from core.devices.power_management_handler import PowerManagementHandler
except Exception:
    PowerManagementHandler = None

# 6.4: declarative registry for lazy FeatureHandler attachment (replaces 21 _maybe_attach_* methods)
HANDLER_ATTACHMENTS = {
    "litra": {
        "device_attr": "_litra_device",
        "handler_cls": LitraIlluminationHandler,
        "feature_attr": "_litra_illumination_idx",
        "handler_name": "litra_illumination",
        "device_name_fallback": "Litra",
    },
    "battery": {
        "device_attr": "_battery_device",
        "handler_cls": BatteryHandler,
        "feature_attr": "_battery_idx",
        "handler_name": "battery",
        "device_name_fallback": "Device",
    },
    "smart_shift": {
        "device_attr": "_smart_shift_device",
        "handler_cls": SmartShiftHandler,
        "feature_attr": "_smart_shift_idx",
        "handler_name": "smart_shift",
        "device_name_fallback": "Device",
    },
    "dpi": {
        "device_attr": "_dpi_device",
        "handler_cls": DPIHandler,
        "feature_attr": "_dpi_idx",
        "handler_name": "dpi",
        "device_name_fallback": "Device",
    },
    "backlight": {
        "device_attr": "_backlight_device",
        "handler_cls": BacklightHandler,
        "feature_attr": "_backlight2_idx",
        "handler_name": "backlight",
        "device_name_fallback": "Device",
    },
    "fn_inversion": {
        "device_attr": "_fn_inversion_device",
        "handler_cls": FnInversionHandler,
        "feature_attr": "_fn_inversion_idx",
        "handler_name": "fn_inversion",
        "device_name_fallback": "Device",
    },
    "report_rate": {
        "device_attr": "_report_rate_device",
        "handler_cls": ReportRateHandler,
        "feature_attr": "_report_rate_idx",
        "handler_name": "report_rate",
        "device_name_fallback": "Device",
    },
    "onboard_profiles": {
        "device_attr": "_onboard_profiles_device",
        "handler_cls": OnboardProfilesHandler,
        "feature_attr": "_onboard_profiles_idx",
        "handler_name": "onboard_profiles",
        "device_name_fallback": "Device",
    },
    "device_name": {
        "device_attr": "_device_name_device",
        "handler_cls": DeviceNameHandler,
        "feature_attr": "_device_name_idx",
        "handler_name": "device_name",
        "device_name_fallback": "Device",
    },
    "led": {
        "device_attr": "_led_device",
        "handler_cls": LEDHandler,
        "feature_attr": "_led_control_idx",
        "handler_name": "led",
        "device_name_fallback": "Device",
    },
    "device_mode": {
        "device_attr": "_device_mode_device",
        "handler_cls": DeviceModeHandler,
        "feature_attr": "_device_mode_idx",
        "handler_name": "device_mode",
        "device_name_fallback": "Device",
    },
    "wireless_power": {
        "device_attr": "_wireless_power_device",
        "handler_cls": WirelessPowerHandler,
        "feature_attr": "_wireless_power_idx",
        "handler_name": "wireless_power",
        "device_name_fallback": "Device",
    },
    "led_effects": {
        "device_attr": "_led_effects_device",
        "handler_cls": LEDEffectsHandler,
        "feature_attr": "_led_effects_idx",
        "handler_name": "led_effects",
        "device_name_fallback": "Device",
    },
    "wireless_channel": {
        "device_attr": "_wireless_channel_device",
        "handler_cls": WirelessChannelHandler,
        "feature_attr": "_wireless_channel_idx",
        "handler_name": "wireless_channel",
        "device_name_fallback": "Device",
    },
    "sleep_timeout": {
        "device_attr": "_sleep_timeout_device",
        "handler_cls": SleepTimeoutHandler,
        "feature_attr": "_sleep_timeout_idx",
        "handler_name": "sleep_timeout",
        "device_name_fallback": "Device",
    },
    "wireless_status": {
        "device_attr": "_wireless_status_device",
        "handler_cls": WirelessStatusHandler,
        "feature_attr": "_wireless_status_idx",
        "handler_name": "wireless_status",
        "device_name_fallback": "Device",
    },
    "device_identity": {
        "device_attr": "_device_identity_device",
        "handler_cls": DeviceIdentityHandler,
        "feature_attr": "_device_identity_idx",
        "handler_name": "device_identity",
        "device_name_fallback": "Device",
    },
    "device_type": {
        "device_attr": "_device_type_device",
        "handler_cls": DeviceTypeHandler,
        "feature_attr": "_device_type_idx",
        "handler_name": "device_type",
        "device_name_fallback": "Device",
    },
    "remaining_pairing": {
        "device_attr": "_remaining_pairing_device",
        "handler_cls": RemainingPairingHandler,
        "feature_attr": "_remaining_pairing_idx",
        "handler_name": "remaining_pairing",
        "device_name_fallback": "Device",
    },
    "force_sensing_button": {
        "device_attr": "_force_sensing_button_device",
        "handler_cls": ForceSensingButtonHandler,
        "feature_attr": "_force_sensing_button_idx",
        "handler_name": "force_sensing_button",
        "device_name_fallback": "Device",
    },
    "power_management": {
        "device_attr": "_power_management_device",
        "handler_cls": PowerManagementHandler,
        "feature_attr": "_power_management_idx",
        "handler_name": "power_management",
        "device_name_fallback": "Device",
    },
}

HSCROLL_ACTION_COOLDOWN_S = 0.35
HSCROLL_VOLUME_COOLDOWN_S = 0.06
_VOLUME_ACTIONS = {"volume_up", "volume_down"}


class Engine:
    """
    Core logic: reads config, installs the mouse hook,
    dispatches actions when mapped buttons are pressed,
    and auto-switches profiles when the foreground app changes.
    """

    def __init__(self):
        self.hook = MouseHook()
        self.cfg = load_config()
        self._enabled = True
        self._hscroll_state = {
            MouseEvent.HSCROLL_LEFT: {"accum": 0.0, "last_fire_at": 0.0},
            MouseEvent.HSCROLL_RIGHT: {"accum": 0.0, "last_fire_at": 0.0},
        }
        self._current_profile: str = self.cfg.get("active_profile", "default")
        self._app_detector = AppDetector(self._on_app_change)
        self._profile_change_cb = None       # UI callback
        self._connection_change_cb = None   # UI callback for device status
        self._status_cb = None             # UI callback for status messages
        self._battery_read_cb = None        # UI callback for battery level
        self._dpi_read_cb = None            # UI callback for current DPI
        self._smart_shift_read_cb = None   # UI callback for Smart Shift mode
        self._debug_cb = None               # UI callback for debug messages
        self._gesture_event_cb = None       # UI callback for structured gesture events
        self._debug_events_enabled = bool(
            self.cfg.get("settings", {}).get("debug_mode", False)
        )
        self._battery_poll_stop = threading.Event()
        self._battery_poll_thread = None          # track the poller thread
        self._last_connection_state = bool(self._hid_runtime_state().input_ready)
        self._last_hid_features_ready = bool(self.hid_features_ready)
        self._hid_replay_requested_this_launch = False
        self._replay_inflight = False
        self._replay_pending_rerun = False
        self._replay_lock = threading.Lock()
        self._mouse_release_timers = {}   # action_id → Timer for safety auto-release
        self._lock = threading.Lock()
        self._selected_device_key = str(
            self.cfg.get("settings", {}).get("selected_device_key", "") or ""
        )
        self.hook.set_debug_callback(self._emit_debug)
        self.hook.set_gesture_callback(self._emit_gesture_event)
        self.hook.set_status_callback(self._emit_status)
        self._setup_hooks()
        self.hook.set_connection_change_callback(self._on_connection_change)
        # Apply persisted DPI setting
        dpi = self.cfg.get("settings", {}).get("dpi", 1000)
        try:
            if hasattr(self.hook, "set_dpi"):
                self.hook.set_dpi(dpi)
        except Exception as e:
            print(f"[Engine] Failed to set DPI: {e}")

    def _hid_runtime_state(self):
        state = getattr(self.hook, "hid_runtime_state", None)
        if state is not None:
            return state
        hg = getattr(self.hook, "_hid_gesture", None)
        hid_device = getattr(hg, "connected_device", None) if hg else None
        return HidRuntimeState(
            input_ready=bool(getattr(self.hook, "device_connected", False)),
            hid_ready=hid_device is not None,
            connected_device=getattr(self.hook, "connected_device", None),
        )

    # ------------------------------------------------------------------
    # Hook wiring
    # ------------------------------------------------------------------
    def _setup_hooks(self):
        """Register callbacks and block events for all mapped buttons."""
        mappings = get_active_mappings(self.cfg)

        # Apply scroll inversion settings to the hook
        settings = self.cfg.get("settings", {})
        self.hook.invert_vscroll = settings.get("invert_vscroll", False)
        self.hook.invert_hscroll = settings.get("invert_hscroll", False)
        if hasattr(self.hook, "ignore_trackpad"):
            self.hook.ignore_trackpad = settings.get("ignore_trackpad", True)
        self.hook.debug_mode = self._debug_events_enabled
        self.hook.configure_gestures(
            enabled=any(mappings.get(key, "none") != "none"
                        for key in GESTURE_DIRECTION_BUTTONS),
            threshold=settings.get("gesture_threshold", 50),
            deadzone=settings.get("gesture_deadzone", 40),
            timeout_ms=settings.get("gesture_timeout_ms", 3000),
            cooldown_ms=settings.get("gesture_cooldown_ms", 500),
        )
        # Divert mode shift CID only when the device has the button and
        # at least one profile maps it to an action.  When no device is
        # connected yet, assume the button exists (safe: if the device
        # turns out not to have it, the divert simply has no effect).
        device = self.active_mouse_device
        device_buttons = getattr(device, "supported_buttons", None)
        has_mode_shift = device_buttons is None or "mode_shift" in device_buttons
        self.hook.divert_mode_shift = (
            has_mode_shift
            and any(
                pdata.get("mappings", {}).get("mode_shift", "none") != "none"
                for pdata in self.cfg.get("profiles", {}).values()
            )
        )

        # Divert DPI switch CID (0x00FD) on MX Vertical when mapped.
        has_dpi_switch = device_buttons is None or "dpi_switch" in device_buttons
        self.hook.divert_dpi_switch = (
            has_dpi_switch
            and any(
                pdata.get("mappings", {}).get("dpi_switch", "none") != "none"
                for pdata in self.cfg.get("profiles", {}).values()
            )
        )

        self._emit_mapping_snapshot("Hook mappings refreshed", mappings)

        for btn_key, action_id in mappings.items():
            events = list(BUTTON_TO_EVENTS.get(btn_key, ()))
            has_paired_down = any(e.endswith("_down") for e in events)
            has_up = any(e.endswith("_up") for e in events)

            for evt_type in events:
                if has_paired_down and evt_type.endswith("_up"):
                    if action_id != "none":
                        self.hook.block(evt_type)
                        if is_mouse_button_action(action_id):
                            self.hook.register(evt_type, self._make_mouse_up_handler(action_id))
                    continue

                if action_id != "none":
                    self.hook.block(evt_type)

                    if "hscroll" in evt_type:
                        self.hook.register(evt_type, self._make_hscroll_handler(action_id))
                    elif is_mouse_button_action(action_id):
                        if has_up:
                            # Button has a matching _up event → split press/release
                            self.hook.register(evt_type, self._make_mouse_down_handler(action_id))
                        else:
                            # Single-fire event (gesture, swipe) → full click
                            self.hook.register(evt_type, self._make_handler(action_id))
                    else:
                        self.hook.register(evt_type, self._make_handler(action_id))

    def _make_handler(self, action_id):
        def handler(event):
            try:
                if self._enabled:
                    self._emit_debug(
                        f"Mapped {event.event_type} -> {action_id} "
                        f"({self._action_label(action_id)})"
                    )
                    if event.event_type.startswith("gesture_"):
                        self._emit_gesture_event({
                            "type": "mapped",
                            "event_name": event.event_type,
                            "action_id": action_id,
                            "action_label": self._action_label(action_id),
                        })
                    if action_id == "toggle_smart_shift":
                        self._toggle_smart_shift()
                    elif action_id == "switch_scroll_mode":
                        self._switch_scroll_mode()
                    elif action_id == "cycle_dpi":
                        self._cycle_dpi()
                    else:
                        execute_action(action_id)
            except Exception as exc:
                print(f"[Engine] _make_handler EXCEPTION for {action_id}: {exc}")
                import traceback; traceback.print_exc()
        return handler

    def _make_mouse_down_handler(self, action_id):
        def _safety_release():
            """Auto-release if the UP event never fires."""
            try:
                print(f"[Engine] SAFETY RELEASE fired for {action_id} (UP never received)")
                self._mouse_release_timers.pop(action_id, None)
                inject_mouse_up(action_id)
            except Exception as exc:
                print(f"[Engine] _safety_release EXCEPTION for {action_id}: {exc}")
                import traceback; traceback.print_exc()

        def handler(event):
            try:
                if self._enabled:
                    self._emit_debug(
                        f"Mapped {event.event_type} -> {action_id} (mouse down)"
                    )
                    inject_mouse_down(action_id)
                    # Safety: auto-release after 20s if UP event is never received
                    old = self._mouse_release_timers.pop(action_id, None)
                    if old is not None:
                        old.cancel()
                    t = threading.Timer(20.0, _safety_release)
                    t.daemon = True
                    self._mouse_release_timers[action_id] = t
                    t.start()
            except Exception as exc:
                print(f"[Engine] mouse_down_handler EXCEPTION for {action_id}: {exc}")
                import traceback; traceback.print_exc()
        return handler

    def _make_mouse_up_handler(self, action_id):
        def handler(event):
            try:
                if self._enabled:
                    self._emit_debug(
                        f"Mapped {event.event_type} -> {action_id} (mouse up)"
                    )
                    # Cancel safety timer
                    old = self._mouse_release_timers.pop(action_id, None)
                    if old is not None:
                        old.cancel()
                    inject_mouse_up(action_id)
            except Exception as exc:
                print(f"[Engine] mouse_up_handler EXCEPTION for {action_id}: {exc}")
                import traceback; traceback.print_exc()
        return handler

    def _toggle_smart_shift(self):
        """Toggle SmartShift auto-switching on/off.

        IMPORTANT: this is called from a HID event callback which runs on the HID
        loop thread.  Calling hg.set_smart_shift() directly would block waiting for
        the same loop to process the pending request — a deadlock that causes the
        3-second timeout seen in the logs.  Config and UI are updated synchronously;
        the device write is dispatched to a separate thread.
        """
        settings = self.cfg.get("settings", {})
        new_enabled = not settings.get("smart_shift_enabled", False)
        mode = settings.get("smart_shift_mode", "ratchet")
        threshold = settings.get("smart_shift_threshold", 25)
        print(f"[Engine] toggle_smart_shift -> enabled={new_enabled}")
        settings["smart_shift_enabled"] = new_enabled
        save_config(self.cfg)
        if self._smart_shift_read_cb:
            try:
                self._smart_shift_read_cb({"mode": mode, "enabled": new_enabled, "threshold": threshold})
            except Exception:
                pass
        hg = self.hook._hid_gesture
        if hg:
            def _write():
                ok = hg.set_smart_shift(mode, new_enabled, threshold)
                print(f"[Engine] toggle_smart_shift device write -> {'OK' if ok else 'FAILED'}")
            threading.Thread(target=_write, daemon=True, name="ToggleSmartShift").start()

    def _switch_scroll_mode(self):
        """Switch between ratchet and free-spin (Logi Options+ physical button behaviour).

        SmartShift auto-switching is disabled so the chosen fixed mode takes effect.
        Same deadlock caveat as _toggle_smart_shift — device write runs off-thread.
        """
        settings = self.cfg.get("settings", {})
        current_mode = settings.get("smart_shift_mode", "ratchet")
        new_mode = "freespin" if current_mode == "ratchet" else "ratchet"
        threshold = settings.get("smart_shift_threshold", 25)
        print(f"[Engine] switch_scroll_mode -> {new_mode}")
        settings["smart_shift_mode"] = new_mode
        settings["smart_shift_enabled"] = False
        save_config(self.cfg)
        if self._smart_shift_read_cb:
            try:
                self._smart_shift_read_cb({"mode": new_mode, "enabled": False, "threshold": threshold})
            except Exception:
                pass
        hg = self.hook._hid_gesture
        if hg:
            def _write():
                ok = hg.set_smart_shift(new_mode, False, threshold)
                print(f"[Engine] switch_scroll_mode device write -> {'OK' if ok else 'FAILED'}")
            threading.Thread(target=_write, daemon=True, name="SwitchScrollMode").start()

    _DEFAULT_DPI_PRESETS = [800, 1200, 1600, 2400]

    def _cycle_dpi(self):
        """Cycle through user-configured DPI presets.

        Advances to the next preset in the list.  If the current DPI doesn't
        match any preset, jumps to the first one.  Updates config, notifies
        the UI, and writes to the device off-thread.
        """
        settings = self.cfg.setdefault("settings", {})
        presets = settings.get("dpi_presets") or list(self._DEFAULT_DPI_PRESETS)
        if not presets:
            return
        current_dpi = settings.get("dpi", 1000)
        try:
            idx = presets.index(current_dpi)
            next_idx = (idx + 1) % len(presets)
        except ValueError:
            next_idx = 0
        new_dpi = clamp_dpi(presets[next_idx], self.active_mouse_device)
        print(f"[Engine] cycle_dpi {current_dpi} -> {new_dpi} (preset {next_idx + 1}/{len(presets)})")
        settings["dpi"] = new_dpi
        save_config(self.cfg)
        if self._dpi_read_cb:
            try:
                self._dpi_read_cb(new_dpi)
            except Exception:
                pass
        hg = self.hook._hid_gesture
        if hg:
            def _write():
                hg.set_dpi(new_dpi)
            threading.Thread(target=_write, daemon=True, name="CycleDPI").start()

    def _make_hscroll_handler(self, action_id):
        def handler(event):
            if not self._enabled:
                return
            state = self._hscroll_state.setdefault(
                event.event_type,
                {"accum": 0.0, "last_fire_at": 0.0},
            )
            step = self._hscroll_step(event.raw_data)
            threshold = self._hscroll_threshold()
            now = getattr(event, "timestamp", None) or time.time()

            cooldown = HSCROLL_VOLUME_COOLDOWN_S if action_id in _VOLUME_ACTIONS else HSCROLL_ACTION_COOLDOWN_S
            if now - state["last_fire_at"] < cooldown:
                state["accum"] = 0.0
                return

            state["accum"] += step
            if state["accum"] < threshold:
                return

            state["accum"] = 0.0
            state["last_fire_at"] = now
            self._emit_debug(
                f"Mapped {event.event_type} -> {action_id} "
                f"({self._action_label(action_id)})"
            )
            execute_action(action_id)
        return handler

    def _hscroll_step(self, raw_value):
        if not isinstance(raw_value, (int, float)):
            return 1.0

        # Treat large wheel deltas as a single logical step while preserving
        # sub-step deltas from macOS event tap scrolling.
        return min(abs(float(raw_value)), 1.0)

    def _hscroll_threshold(self):
        return max(
            0.1,
            float(self.cfg.get("settings", {}).get("hscroll_threshold", 1)),
        )

    # ------------------------------------------------------------------
    # Per-app auto-switching
    # ------------------------------------------------------------------
    def _on_app_change(self, exe_name: str):
        """Called by AppDetector when foreground window changes."""
        target = get_profile_for_app(self.cfg, exe_name)
        if target == self._current_profile:
            return
        print(f"[Engine] App changed to {exe_name} -> profile '{target}'")
        self._switch_profile(target)

    def _switch_profile(self, profile_name: str):
        with self._lock:
            self.cfg["active_profile"] = profile_name
            self._current_profile = profile_name
            # Lightweight: just re-wire callbacks, keep hook + HID++ alive
            self.hook.reset_bindings()
            self._setup_hooks()
            self._emit_debug(f"Active profile -> {profile_name}")
        # Notify UI (if connected)
        if self._profile_change_cb:
            try:
                self._profile_change_cb(profile_name)
            except Exception:
                pass

    def set_profile_change_callback(self, cb):
        """Register a callback ``cb(profile_name)`` invoked on auto-switch."""
        self._profile_change_cb = cb

    def set_debug_callback(self, cb):
        """Register ``cb(message: str)`` invoked for debug events."""
        self._debug_cb = cb

    def set_status_callback(self, cb):
        """Register ``cb(message: str)`` invoked for status messages."""
        self._status_cb = cb

    def set_gesture_event_callback(self, cb):
        """Register ``cb(event: dict)`` invoked for structured gesture debug events."""
        self._gesture_event_cb = cb

    def set_debug_enabled(self, enabled):
        enabled = bool(enabled)
        self.cfg.setdefault("settings", {})["debug_mode"] = enabled
        self._debug_events_enabled = enabled
        self.hook.debug_mode = enabled
        if enabled:
            self._emit_debug(f"Debug enabled on profile {self._current_profile}")
            self._emit_mapping_snapshot(
                "Current mappings", get_active_mappings(self.cfg)
            )

    def set_debug_events_enabled(self, enabled):
        self._debug_events_enabled = bool(enabled)
        self.hook.debug_mode = self._debug_events_enabled

    def _action_label(self, action_id):
        return ACTIONS.get(action_id, {}).get("label", action_id)

    def _emit_debug(self, message):
        if not self._debug_events_enabled:
            return
        if self._debug_cb:
            try:
                self._debug_cb(message)
            except Exception:
                pass

    def _emit_status(self, message):
        if self._status_cb:
            try:
                self._status_cb(message)
            except Exception:
                pass

    def _emit_gesture_event(self, event):
        if not self._debug_events_enabled:
            return
        if self._gesture_event_cb:
            try:
                self._gesture_event_cb(event)
            except Exception:
                pass

        # 007.4/007.5: Make the diverted MX Mechanical Mini backlight key events mappable
        # They arrive as strings via the gesture callback when diversion is opted in.
        if isinstance(event, str) and event.startswith("keyboard_backlight_"):
            mappings = get_active_mappings(self.cfg)
            action_id = mappings.get(event, "none")

            # Also check friendly canonical aliases (backlight_up / backlight_down)
            if action_id == "none":
                if event in ("keyboard_backlight_up_down", "keyboard_backlight_up_up"):
                    action_id = mappings.get("backlight_up", "none")
                elif event in ("keyboard_backlight_down_down", "keyboard_backlight_down_up"):
                    action_id = mappings.get("backlight_down", "none")

            if action_id != "none":
                try:
                    execute_action(action_id)
                    self._emit_debug(f"Diverted Backlight key triggered mapped action: {action_id} (event: {event})")
                except Exception as exc:
                    print(f"[Engine] Exception executing action for diverted {event}: {exc}")

    def _emit_mapping_snapshot(self, prefix, mappings):
        if not self._debug_events_enabled:
            return
        interesting = [
            "gesture",
            "gesture_left",
            "gesture_right",
            "gesture_up",
            "gesture_down",
            "xbutton1",
            "xbutton2",
            # 007.4/007.5: Diverted MX Mechanical Mini backlight keys (opt-in)
            "keyboard_backlight_up",
            "keyboard_backlight_down",
            "backlight_up",
            "backlight_down",
        ]
        summary = ", ".join(f"{key}={mappings.get(key, 'none')}" for key in interesting)
        self._emit_debug(f"{prefix}: {summary}")

    def _saved_smart_shift_state(self):
        settings = self.cfg.get("settings", {})
        return {
            "mode": settings.get("smart_shift_mode", "ratchet"),
            "enabled": settings.get("smart_shift_enabled", False),
            "threshold": settings.get("smart_shift_threshold", 25),
        }

    def _run_saved_settings_replay(self):
        hg = self.hook._hid_gesture
        if hg is None:
            return False
        if hasattr(hg, "connected_device") and hg.connected_device is None:
            return False

        replay_ok = True
        retry_dpi = False
        retry_smart_shift = False
        saved_dpi = self.cfg.get("settings", {}).get("dpi")

        saved_ss_state = self._saved_smart_shift_state()
        saved_ss = saved_ss_state["mode"]
        ss_enabled = saved_ss_state["enabled"]
        ss_threshold = saved_ss_state["threshold"]

        # Phase A: apply Smart Shift immediately so the physical wheel mode
        # converges before the settled replay.
        if saved_ss and getattr(hg, "smart_shift_supported", False):
            if not hasattr(hg, "set_smart_shift"):
                replay_ok = False
            else:
                if not hg.set_smart_shift(saved_ss, ss_enabled, ss_threshold):
                    replay_ok = False
                if self._smart_shift_read_cb:
                    try:
                        self._smart_shift_read_cb(saved_ss_state)
                    except Exception:
                        pass

        time.sleep(3)
        hg = self.hook._hid_gesture
        if hg is None or getattr(hg, "connected_device", None) is None:
            return False

        if saved_dpi is not None:
            if not hasattr(hg, "set_dpi"):
                replay_ok = False
            elif hg.set_dpi(saved_dpi):
                if self._dpi_read_cb:
                    try:
                        self._dpi_read_cb(saved_dpi)
                    except Exception:
                        pass
            else:
                replay_ok = False
                retry_dpi = True

        if saved_ss and getattr(hg, "smart_shift_supported", False):
            if not hasattr(hg, "set_smart_shift"):
                replay_ok = False
            elif hg.set_smart_shift(saved_ss, ss_enabled, ss_threshold):
                if self._smart_shift_read_cb:
                    try:
                        self._smart_shift_read_cb(saved_ss_state)
                    except Exception:
                        pass
            else:
                replay_ok = False
                retry_smart_shift = True

        if retry_dpi or retry_smart_shift:
            time.sleep(5)
            hg = self.hook._hid_gesture
            if hg is None or getattr(hg, "connected_device", None) is None:
                return False
            if retry_dpi:
                if not hasattr(hg, "set_dpi") or not hg.set_dpi(saved_dpi):
                    replay_ok = False
                elif self._dpi_read_cb:
                    try:
                        self._dpi_read_cb(saved_dpi)
                    except Exception:
                        pass
            if retry_smart_shift and getattr(hg, "smart_shift_supported", False):
                if not hasattr(hg, "set_smart_shift") or not hg.set_smart_shift(
                    saved_ss, ss_enabled, ss_threshold
                ):
                    replay_ok = False
                elif self._smart_shift_read_cb:
                    try:
                        self._smart_shift_read_cb(saved_ss_state)
                    except Exception:
                        pass

        if not self._replay_saved_keyboard_host_settings(hg):
            replay_ok = False

        return replay_ok

    def _replay_saved_settings_worker(self):
        while True:
            with self._replay_lock:
                self._replay_pending_rerun = False
            replay_ok = self._run_saved_settings_replay()
            should_emit_failure = False
            with self._replay_lock:
                if self._replay_pending_rerun:
                    continue
                self._replay_inflight = False
                should_emit_failure = not replay_ok
            if should_emit_failure:
                self._emit_status(
                    "Mouse reconnected, but saved device settings could not be restored yet."
                )
            return

    def _request_saved_settings_replay(self, *, startup_fallback=False):
        with self._replay_lock:
            if startup_fallback and self._hid_replay_requested_this_launch:
                return
            if self._replay_inflight:
                self._replay_pending_rerun = True
                return
            self._hid_replay_requested_this_launch = True
            self._replay_inflight = True
        if startup_fallback:
            self._emit_status("Using startup fallback to replay saved device settings")
        threading.Thread(
            target=self._replay_saved_settings_worker,
            daemon=True,
            name="SavedSettingsReplay",
        ).start()

    def _on_connection_change(self, connected):
        connection_changed = connected != self._last_connection_state
        hid_features_ready = self.hid_features_ready
        hid_features_changed = hid_features_ready != self._last_hid_features_ready
        if connection_changed:
            self._last_connection_state = connected
            self._battery_poll_stop.set()
            if self._battery_poll_thread is not None:
                self._battery_poll_thread.join(timeout=5)
                self._battery_poll_thread = None
        self._last_hid_features_ready = hid_features_ready
        if self._connection_change_cb:
            try:
                self._connection_change_cb(connected)
            except Exception:
                pass
        if connected and connection_changed:
            self._battery_poll_stop = threading.Event()
            self._battery_poll_thread = threading.Thread(
                target=self._battery_poll_loop,
                args=(self._battery_poll_stop,),
                daemon=True,
                name="BatteryPoll",
            )
            self._battery_poll_thread.start()
        if hid_features_ready and hid_features_changed:
            self._request_saved_settings_replay()

    def _battery_poll_loop(self, stop_event):
        """Read battery and smart shift mode periodically until disconnected."""
        _battery_poll_interval = 300   # seconds between battery reads
        _ss_poll_interval = 15         # seconds between scroll-mode reads
        _last_battery = time.time() - _battery_poll_interval  # fire immediately
        _last_ss = time.time() - _ss_poll_interval            # fire immediately
        _last_ss_mode = None

        while not stop_event.is_set():
            now = time.time()
            hg = self.hook._hid_gesture
            if hg and hg.connected_device is not None:
                if now - _last_battery >= _battery_poll_interval:
                    _last_battery = now
                    # 009.2: lazy attachment + optional delegation to BatteryHandler
                    self._maybe_attach_handler("battery")
                    level = None
                    if BatteryHandler is not None and hasattr(self, "_battery_device") and self._battery_device:
                        handler = self._battery_device.get_handler("battery")
                        if handler:
                            level = handler.handle_read()
                    if level is None:
                        level = hg.read_battery()

                    if stop_event.is_set():
                        return
                    if level is not None and self._battery_read_cb:
                        try:
                            self._battery_read_cb(level)
                        except Exception:
                            pass

                if (
                    not self._replay_inflight
                    and now - _last_ss >= _ss_poll_interval
                    and hg.smart_shift_supported
                ):
                    _last_ss = now
                    ss_mode = hg.read_smart_shift()
                    if stop_event.is_set():
                        return
                    if ss_mode is not None:
                        if ss_mode != _last_ss_mode:
                            print(f"[Engine] Scroll mode: {ss_mode}"
                                  + (" (changed)" if _last_ss_mode is not None else ""))
                            _last_ss_mode = ss_mode
                        if self._smart_shift_read_cb:
                            try:
                                self._smart_shift_read_cb(ss_mode)
                            except Exception:
                                pass

            if stop_event.wait(5):
                return

    def set_battery_callback(self, cb):
        """Register ``cb(level: int)`` invoked when battery level is read (0-100)."""
        self._battery_read_cb = cb

    def set_connection_change_callback(self, cb):
        """Register ``cb(connected: bool)`` invoked on device connect/disconnect."""
        self._connection_change_cb = cb
        if cb:
            try:
                cb(bool(self._hid_runtime_state().input_ready))
            except Exception:
                pass

    @property
    def device_connected(self):
        return self._hid_runtime_state().input_ready

    @property
    def connected_device(self):
        return self._hid_runtime_state().connected_device

    @property
    def active_mouse_device(self):
        """Mouse used for button remapping and DPI. MVP alias of connected_device when kind is mouse."""
        return active_mouse_device_from_connected(self.connected_device)

    @property
    def selected_device_key(self) -> str:
        """UI-selected device key (keyboard/Litra context). Synced from Backend.selectedDeviceKey."""
        return self._selected_device_key

    @selected_device_key.setter
    def selected_device_key(self, value: str) -> None:
        normalized = str(value or "")
        if normalized == self._selected_device_key:
            return
        self._selected_device_key = normalized
        self.cfg.setdefault("settings", {})["selected_device_key"] = normalized
        save_config(self.cfg)

    @property
    def all_devices(self) -> list[dict]:
        """All known devices: config entries plus the currently connected device."""
        return build_all_devices_list(
            self.cfg,
            self.connected_device,
            mouse_connected=self.device_connected,
        )

    def dump_device_info(self):
        return getattr(self.hook, "dump_device_info", lambda: None)()

    @property
    def hid_features_ready(self):
        return self._hid_runtime_state().hid_ready

    @property
    def enabled(self):
        return self._enabled

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_dpi(self, dpi_value):
        """Send DPI change to the mouse via HID++."""
        dpi = clamp_dpi(dpi_value, self.active_mouse_device)
        self.cfg.setdefault("settings", {})["dpi"] = dpi
        save_config(self.cfg)

        # 009.4: optional delegation to DPIHandler (full backward compatibility fallback)
        self._maybe_attach_handler("dpi")
        if DPIHandler is not None and hasattr(self, "_dpi_device") and self._dpi_device:
            handler = self._dpi_device.get_handler("dpi")
            if handler:
                return handler.handle_write(dpi)

        # Try via the hook's HidGestureListener (original path)
        hg = self.hook._hid_gesture
        if hg:
            return hg.set_dpi(dpi)
        print("[Engine] No HID++ connection — DPI not applied")
        return False

    def set_smart_shift(self, mode, smart_shift_enabled=False, threshold=25):
        """Send Smart Shift settings to device.
        mode: 'ratchet' or 'freespin' (fixed mode when smart_shift_enabled=False)
        smart_shift_enabled: True to enable auto SmartShift
        threshold: 1-50 sensitivity when SmartShift is enabled"""
        print(f"[Engine] set_smart_shift({mode}, enabled={smart_shift_enabled}, threshold={threshold}) called")
        settings = self.cfg.setdefault("settings", {})
        settings["smart_shift_mode"] = mode
        settings["smart_shift_enabled"] = smart_shift_enabled
        settings["smart_shift_threshold"] = threshold
        save_config(self.cfg)

        def _fallback():
            hg = self.hook._hid_gesture
            if hg:
                result = hg.set_smart_shift(mode, smart_shift_enabled, threshold)
                print(f"[Engine] set_smart_shift -> {'OK' if result else 'FAILED'}")
                return result
            print("[Engine] set_smart_shift: No HID++ connection — not applied")
            return False

        self._maybe_attach_handler("smart_shift")
        return self._delegate_or_fallback(
            "_smart_shift_device", "smart_shift", "handle_write",
            _fallback, mode, smart_shift_enabled, threshold
        )

    @property
    def smart_shift_supported(self):
        hg = self.hook._hid_gesture
        return hg.smart_shift_supported if hg else False

    def read_smart_shift(self):
        """Read current SmartShift state from device."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg:
                return hg.read_smart_shift()
            return None

        self._maybe_attach_handler("smart_shift")
        return self._delegate_or_fallback(
            "_smart_shift_device", "smart_shift", "handle_read",
            _fallback
        )

    # ------------------------------------------------------------------
    # Keyboard middle-path (MX Mechanical Mini etc.) — host-side only, temporary
    # ------------------------------------------------------------------

    def read_backlight(self):
        """Returns [enabled, level] or [None, None]. Host-side only, temporary (lost on reconnect/host switch)."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg:
                return hg.read_backlight()
            return [None, None]

        self._maybe_attach_handler("backlight")
        return self._delegate_or_fallback(
            "_backlight_device", "backlight", "handle_read",
            _fallback
        )

    def set_backlight(self, enabled, level=-1):
        """Host-side backlight control. Temporary (lost on reconnect/host switch)."""
        # Respect per-device middle-path setting (006.2)
        device = getattr(self, "connected_device", None)
        device_key = getattr(device, "key", None) if device else None
        if not device_key and device:
            device_key = str(getattr(device, "product_id", "unknown"))
        if device_key:
            kmp = get_keyboard_middle_path_settings(self.cfg, device_key)
            if not kmp.get("allow_host_backlight", True):
                print(f"[Engine] set_backlight blocked by per-device setting (device={device_key})")
                return False

        lvl = None if level < 0 else level

        def _fallback():
            hg = self.hook._hid_gesture
            if hg:
                return hg.set_backlight(bool(enabled), lvl)
            print("[Engine] set_backlight: No HID++ connection — not applied")
            return False

        self._maybe_attach_handler("backlight")
        ok = self._delegate_or_fallback(
            "_backlight_device", "backlight", "handle_write",
            _fallback, bool(enabled), lvl
        )
        if ok and device_key:
            save_keyboard_host_backlight_state(self.cfg, device_key, bool(enabled), lvl)
        return ok

    def read_fn_inversion(self):
        """Returns current Fn/Fx swap state or False/None. Host-side only, temporary."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg:
                val = hg.read_fn_inversion()
                return val if val is not None else False
            return False

        self._maybe_attach_handler("fn_inversion")
        val = self._delegate_or_fallback(
            "_fn_inversion_device", "fn_inversion", "handle_read",
            _fallback
        )
        return val if val is not None else False

    def set_fn_inversion(self, swap):
        """Host-side FN inversion toggle. Temporary (lost on reconnect/host switch)."""
        # Respect per-device middle-path setting (006.2)
        device = getattr(self, "connected_device", None)
        device_key = getattr(device, "key", None) if device else None
        if not device_key and device:
            device_key = str(getattr(device, "product_id", "unknown"))
        if device_key:
            kmp = get_keyboard_middle_path_settings(self.cfg, device_key)
            if not kmp.get("allow_fn_inversion", True):
                print(f"[Engine] set_fn_inversion blocked by per-device setting (device={device_key})")
                return False

        def _fallback():
            hg = self.hook._hid_gesture
            if hg:
                return hg.set_fn_inversion(bool(swap))
            print("[Engine] set_fn_inversion: No HID++ connection — not applied")
            return False

        self._maybe_attach_handler("fn_inversion")
        ok = self._delegate_or_fallback(
            "_fn_inversion_device", "fn_inversion", "handle_write",
            _fallback, bool(swap)
        )
        if ok and device_key:
            save_keyboard_host_fn_inversion_state(self.cfg, device_key, bool(swap))
        return ok

    def has_backlight_control(self):
        """Returns True if the connected device supports host-side BACKLIGHT2 control via this API (MX Mechanical Mini etc.)."""
        hg = self.hook._hid_gesture
        if hg:
            return getattr(hg, "_backlight2_idx", None) is not None
        return False

    def has_fn_inversion_control(self):
        """Returns True if the connected device supports host-side K375S FN inversion control via this API."""
        hg = self.hook._hid_gesture
        if hg:
            return getattr(hg, "_fn_inversion_idx", None) is not None
        return False

    def has_litra_illumination_control(self):
        """True when the active HID++ device exposes ILLUMINATION (Litra Beam etc.)."""
        hg = self.hook._hid_gesture
        if hg:
            return getattr(hg, "_litra_illumination_idx", None) is not None
        return False

    def has_onboard_profile_control(self):
        """True when the connected device supports ONBOARD_PROFILES (0x8100) via HID++."""
        hg = self.hook._hid_gesture
        if hg:
            return getattr(hg, "_onboard_profiles_idx", None) is not None
        return False

    def _keyboard_replay_device_key(self, hg):
        device = getattr(hg, "connected_device", None)
        if not device:
            return None
        key = getattr(device, "key", None)
        if key:
            return key
        product_id = getattr(device, "product_id", None)
        return str(product_id) if product_id is not None else None

    def _replay_saved_keyboard_host_settings(self, hg):
        """Replay per-device host-side keyboard settings after HID++ reconnect."""
        device_key = self._keyboard_replay_device_key(hg)
        if not device_key:
            return True
        kmp = get_keyboard_middle_path_settings(self.cfg, device_key)
        saved = get_saved_keyboard_host_replay(self.cfg, device_key)
        replay_ok = True

        if kmp.get("allow_host_backlight", True) and saved.get("backlight") is not None:
            if getattr(hg, "_backlight2_idx", None) is not None:
                enabled, level = saved["backlight"]
                print(
                    f"[Engine] Replaying host-side backlight (device={device_key}, "
                    f"enabled={enabled}, level={level}) — temporary"
                )
                if not hg.set_backlight(enabled, level):
                    replay_ok = False

        if kmp.get("allow_fn_inversion", True) and saved.get("fn_inversion") is not None:
            if getattr(hg, "_fn_inversion_idx", None) is not None:
                swap = saved["fn_inversion"]
                print(
                    f"[Engine] Replaying host-side FN inversion (device={device_key}, "
                    f"swap={swap}) — temporary"
                )
                if not hg.set_fn_inversion(swap):
                    replay_ok = False

        return replay_ok

    # 009.5: thin public Report Rate wrappers (delegation + full fallback)
    def set_report_rate(self, rate):
        """Set report rate (0x8060). Temporary (lost on reconnect/host switch)."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg:
                return hg.set_report_rate(rate) if hasattr(hg, "set_report_rate") else False
            print("[Engine] set_report_rate: No HID++ connection — not applied")
            return False

        self._maybe_attach_handler("report_rate")
        return self._delegate_or_fallback(
            "_report_rate_device", "report_rate", "handle_write",
            _fallback, rate
        )

    def read_report_rate(self):
        """Read current report rate. Host-side only, temporary."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg:
                return hg.read_report_rate() if hasattr(hg, "read_report_rate") else None
            return None

        self._maybe_attach_handler("report_rate")
        return self._delegate_or_fallback(
            "_report_rate_device", "report_rate", "handle_read",
            _fallback
        )

    # 009.9: thin public Onboard Profiles wrappers (delegation + full fallback)
    def read_onboard_profile(self):
        """Read current onboard profile index. Host-side only, temporary."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg and hasattr(hg, "read_onboard_profile"):
                return hg.read_onboard_profile()
            return None

        self._maybe_attach_handler("onboard_profiles")
        return self._delegate_or_fallback(
            "_onboard_profiles_device", "onboard_profiles", "handle_read",
            _fallback
        )

    def switch_onboard_profile(self, profile_index: int):
        """Switch to the given onboard profile index. Host-side only, temporary."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg and hasattr(hg, "switch_onboard_profile"):
                return hg.switch_onboard_profile(profile_index)
            return False

        self._maybe_attach_handler("onboard_profiles")
        return self._delegate_or_fallback(
            "_onboard_profiles_device", "onboard_profiles", "handle_write",
            _fallback, profile_index
        )

    # 009.15: thin public Device Name wrappers (read-only for this micro-chunk)
    def read_device_name(self):
        """Read current device/friendly name. Host-side only, temporary."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg and hasattr(hg, "read_device_name"):
                return hg.read_device_name()
            return None

        self._maybe_attach_handler("device_name")
        return self._delegate_or_fallback(
            "_device_name_device", "device_name", "handle_read",
            _fallback
        )

    # 009.23: thin public Device Name write wrapper (completes the feature)
    def set_device_name(self, name: str):
        """Set device/friendly name. Host-side only, temporary. Returns success."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg and hasattr(hg, "set_device_name"):
                return hg.set_device_name(name)
            print("[Engine] set_device_name: No HID++ connection — not applied")
            return False

        self._maybe_attach_handler("device_name")
        return self._delegate_or_fallback(
            "_device_name_device", "device_name", "handle_write",
            _fallback, name
        )

    # 009.31: thin public Device Friendly Name (user-settable) wrappers
    def read_device_friendly_name(self):
        """Read the current user-settable Friendly Name. Host-side only, temporary."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg and hasattr(hg, "read_device_friendly_name"):
                return hg.read_device_friendly_name()
            return None

        self._maybe_attach_handler("device_name")
        return self._delegate_or_fallback(
            "_device_name_device", "device_name", "handle_read_friendly_name",
            _fallback
        )

    def set_device_friendly_name(self, name: str):
        """Set the user-settable Friendly Name. Host-side only, temporary. Returns success."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg and hasattr(hg, "set_device_friendly_name"):
                return hg.set_device_friendly_name(name)
            print("[Engine] set_device_friendly_name: No HID++ connection — not applied")
            return False

        self._maybe_attach_handler("device_name")
        return self._delegate_or_fallback(
            "_device_name_device", "device_name", "handle_write_friendly_name",
            _fallback, name
        )

    # 009.16: thin public LED wrappers (host-side only, temporary)
    def set_led_state(self, enabled, brightness=-1):
        """Host-side mouse LED on/off + brightness (0-100). Temporary (lost on reconnect/host switch)."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg:
                lvl = None if brightness < 0 else brightness
                return hg.set_led_state(bool(enabled), lvl)
            print("[Engine] set_led_state: No HID++ connection — not applied")
            return False

        self._maybe_attach_handler("led")
        return self._delegate_or_fallback(
            "_led_device", "led", "handle_write",
            _fallback, bool(enabled), None if brightness < 0 else brightness
        )

    def read_led_state(self):
        """Returns (enabled, brightness) or (None, None). Host-side only, temporary."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg:
                return hg.read_led_state()
            return None, None

        self._maybe_attach_handler("led")
        return self._delegate_or_fallback(
            "_led_device", "led", "handle_read",
            _fallback
        )

    # 009.17: thin public Device Mode wrappers (host-side only, temporary)
    def read_device_mode(self):
        """Read current device mode value. Host-side only, temporary."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg and hasattr(hg, "read_device_mode"):
                return hg.read_device_mode()
            return None

        self._maybe_attach_handler("device_mode")
        return self._delegate_or_fallback(
            "_device_mode_device", "device_mode", "handle_read",
            _fallback
        )

    def set_device_mode(self, mode_value: int):
        """Set device mode. Host-side only, temporary. Returns success."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg and hasattr(hg, "set_device_mode"):
                return hg.set_device_mode(mode_value)
            print("[Engine] set_device_mode: No HID++ connection — not applied")
            return False

        self._maybe_attach_handler("device_mode")
        return self._delegate_or_fallback(
            "_device_mode_device", "device_mode", "handle_write",
            _fallback, mode_value
        )

    # 009.18: thin public Wireless Power wrappers (host-side only, temporary)
    def read_wireless_power(self):
        """Read current wireless power level/mode. Host-side only, temporary."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg and hasattr(hg, "read_wireless_power"):
                return hg.read_wireless_power()
            return None

        self._maybe_attach_handler("wireless_power")
        return self._delegate_or_fallback(
            "_wireless_power_device", "wireless_power", "handle_read",
            _fallback
        )

    def set_wireless_power(self, power_value: int):
        """Set wireless power level/mode. Host-side only, temporary. Returns success."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg and hasattr(hg, "set_wireless_power"):
                return hg.set_wireless_power(power_value)
            print("[Engine] set_wireless_power: No HID++ connection — not applied")
            return False

        self._maybe_attach_handler("wireless_power")
        return self._delegate_or_fallback(
            "_wireless_power_device", "wireless_power", "handle_write",
            _fallback, power_value
        )

    # 009.19: thin public LED Effects wrappers (host-side only, temporary)
    def read_led_effect(self):
        """Read current LED effect state/parameters. Host-side only, temporary."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg and hasattr(hg, "read_led_effect"):
                return hg.read_led_effect()
            return None

        self._maybe_attach_handler("led_effects")
        return self._delegate_or_fallback(
            "_led_effects_device", "led_effects", "handle_read",
            _fallback
        )

    def set_led_effect(self, effect: int, params: list | None = None):
        """Set LED effect and optional parameters. Host-side only, temporary. Returns success."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg and hasattr(hg, "set_led_effect"):
                return hg.set_led_effect(effect, params)
            print("[Engine] set_led_effect: No HID++ connection — not applied")
            return False

        self._maybe_attach_handler("led_effects")
        return self._delegate_or_fallback(
            "_led_effects_device", "led_effects", "handle_write",
            _fallback, effect, params
        )

    # 009.20: thin public Wireless Channel wrappers (host-side only, temporary)
    def read_wireless_channel(self):
        """Read current wireless channel. Host-side only, temporary."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg and hasattr(hg, "read_wireless_channel"):
                return hg.read_wireless_channel()
            return None

        self._maybe_attach_handler("wireless_channel")
        return self._delegate_or_fallback(
            "_wireless_channel_device", "wireless_channel", "handle_read",
            _fallback
        )

    def set_wireless_channel(self, channel_value: int):
        """Set wireless channel. Host-side only, temporary. Returns success."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg and hasattr(hg, "set_wireless_channel"):
                return hg.set_wireless_channel(channel_value)
            print("[Engine] set_wireless_channel: No HID++ connection — not applied")
            return False

        self._maybe_attach_handler("wireless_channel")
        return self._delegate_or_fallback(
            "_wireless_channel_device", "wireless_channel", "handle_write",
            _fallback, channel_value
        )

    # 009.21: thin public Sleep Timeout wrappers (host-side only, temporary)
    def read_sleep_timeout(self):
        """Read current sleep/power-save timeout value. Host-side only, temporary."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg and hasattr(hg, "read_sleep_timeout"):
                return hg.read_sleep_timeout()
            return None

        self._maybe_attach_handler("sleep_timeout")
        return self._delegate_or_fallback(
            "_sleep_timeout_device", "sleep_timeout", "handle_read",
            _fallback
        )

    def set_sleep_timeout(self, timeout_value: int):
        """Set sleep/power-save timeout. Host-side only, temporary. Returns success."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg and hasattr(hg, "set_sleep_timeout"):
                return hg.set_sleep_timeout(timeout_value)
            print("[Engine] set_sleep_timeout: No HID++ connection — not applied")
            return False

        self._maybe_attach_handler("sleep_timeout")
        return self._delegate_or_fallback(
            "_sleep_timeout_device", "sleep_timeout", "handle_write",
            _fallback, timeout_value
        )

    # 009.22: thin public Wireless Status wrapper (host-side only, temporary; read-only)
    def read_wireless_status(self):
        """Read current wireless status values (raw parameters). Host-side only, temporary."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg and hasattr(hg, "read_wireless_status"):
                return hg.read_wireless_status()
            return None

        self._maybe_attach_handler("wireless_status")
        return self._delegate_or_fallback(
            "_wireless_status_device", "wireless_status", "handle_read",
            _fallback
        )

    # 009.24: thin public Device Identity wrapper (host-side only, temporary; read-only)
    def read_device_identity(self):
        """Read basic device serial number / hardware version / identity. Host-side only, temporary."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg and hasattr(hg, "read_device_identity"):
                return hg.read_device_identity()
            return None

        self._maybe_attach_handler("device_identity")
        return self._delegate_or_fallback(
            "_device_identity_device", "device_identity", "handle_read",
            _fallback
        )

    # 009.35: thin public Device Type wrapper (host-side only, temporary; read-only)
    def read_device_type(self):
        """Read basic device type / product type. Host-side only, temporary."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg and hasattr(hg, "read_device_type"):
                return hg.read_device_type()
            return None

        self._maybe_attach_handler("device_type")
        return self._delegate_or_fallback(
            "_device_type_device", "device_type", "handle_read",
            _fallback
        )

    # 009.49 (fresh): thin public Remaining Pairing wrapper (read-only)
    def get_remaining_pairing_slots(self):
        """Returns the number of remaining pairing slots on the receiver, or None. Host-side only, temporary."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg and hasattr(hg, "get_remaining_pairing_slots"):
                return hg.get_remaining_pairing_slots()
            return None

        self._maybe_attach_handler("remaining_pairing")
        return self._delegate_or_fallback(
            "_remaining_pairing_device", "remaining_pairing", "handle_read",
            _fallback
        )

    # 009.51 (fresh): thin public Force Sensing Button wrapper (read-focused)
    def get_force_sensing_buttons(self):
        """Returns force sensing button information (raw or structured) or None. Host-side only, temporary."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg and hasattr(hg, "get_force_sensing_buttons"):
                return hg.get_force_sensing_buttons()
            return None

        self._maybe_attach_handler("force_sensing_button")
        return self._delegate_or_fallback(
            "_force_sensing_button_device", "force_sensing_button", "handle_read",
            _fallback
        )

    # 009.37: thin public Power Management wrappers (host-side only, temporary)
    def read_power_management(self):
        """Read current power management settings / profile. Host-side only, temporary."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg and hasattr(hg, "read_power_management"):
                return hg.read_power_management()
            return None

        self._maybe_attach_handler("power_management")
        return self._delegate_or_fallback(
            "_power_management_device", "power_management", "handle_read",
            _fallback
        )

    def set_power_management(self, settings):
        """Set power management settings / profile. Host-side only, temporary. Returns success."""
        def _fallback():
            hg = self.hook._hid_gesture
            if hg and hasattr(hg, "set_power_management"):
                return hg.set_power_management(settings)
            print("[Engine] set_power_management: No HID++ connection — not applied")
            return False

        self._maybe_attach_handler("power_management")
        return self._delegate_or_fallback(
            "_power_management_device", "power_management", "handle_write",
            _fallback, settings
        )

    # ------------------------------------------------------------------
    # Litra Beam basic illumination (008.2 skeleton, host-side only, temporary)
    # ------------------------------------------------------------------

    def set_litra_illumination(self, enabled, brightness=-1):
        """Host-side Litra Beam illumination control (on/off + brightness 0-100).
        Temporary (lost on reconnect/host switch)."""
        self._maybe_attach_handler("litra")

        def _fallback():
            hg = self.hook._hid_gesture
            if hg:
                lvl = None if brightness < 0 else brightness
                return hg.set_litra_illumination(bool(enabled), lvl)
            print("[Engine] set_litra_illumination: No HID++ connection — not applied")
            return False

        return self._delegate_or_fallback(
            "_litra_device", "litra_illumination", "handle_write",
            _fallback, bool(enabled), None if brightness < 0 else brightness
        )

    def read_litra_illumination(self):
        """Returns (enabled, brightness) or (None, None). Host-side only, temporary."""
        # 009.1: lazy attachment of FeatureHandler (only for Litra devices, zero impact otherwise)
        self._maybe_attach_handler("litra")

        if LitraIlluminationHandler is not None and hasattr(self, "_litra_device") and self._litra_device:
            handler = self._litra_device.get_handler("litra_illumination")
            if handler:
                return handler.handle_read()

        hg = self.hook._hid_gesture
        if hg:
            return hg.read_litra_illumination()
        return None, None

    def _maybe_attach_handler(self, name: str):
        """6.4: declarative lazy attachment via HANDLER_ATTACHMENTS registry."""
        entry = HANDLER_ATTACHMENTS.get(name)
        if not entry:
            return
        handler_cls = entry["handler_cls"]
        if not (handler_cls and hasattr(self, "hook")):
            return
        hg = getattr(self.hook, "_hid_gesture", None)
        feature_attr = entry["feature_attr"]
        if not hg or getattr(hg, feature_attr, None) is None:
            return
        device_attr = entry["device_attr"]
        if not hasattr(self, device_attr) or getattr(self, device_attr) is None:
            connected = getattr(hg, "connected_device", None)
            product_id = getattr(connected, "product_id", 0)
            device_key_fallback = entry.get("device_key_fallback", str(product_id))
            dev = maybe_attach_handler(
                listener=hg,
                handler_cls=handler_cls,
                cfg=self.cfg,
                device_key_fallback=device_key_fallback,
                device_name_fallback=entry["device_name_fallback"],
                product_id_fallback=product_id,
                feature_attr=feature_attr,
                handler_name=entry["handler_name"],
            )
            if dev:
                setattr(self, device_attr, dev)

    # 009.7: tiny reusable helper for the common “delegate or fallback” pattern
    def _delegate_or_fallback(self, device_attr: str, handler_name: str, handler_method: str, fallback_callable, *args, **kwargs):
        """Encapsulates the repetitive delegate-to-handler-or-call-fallback logic.

        device_attr: e.g. "_litra_device"
        handler_name: e.g. "litra_illumination"
        handler_method: e.g. "handle_write"
        fallback_callable: the original listener call (e.g. lambda: hg.set_xxx(...))
        """
        device = getattr(self, device_attr, None)
        if device:
            handler = device.get_handler(handler_name)
            if handler and hasattr(handler, handler_method):
                return getattr(handler, handler_method)(*args, **kwargs)
        # Fallbacks close over listener args; only handler methods receive *args.
        return fallback_callable() if fallback_callable else None

    def reload_mappings(self):
        """
        Called by the UI when the user changes a mapping.
        Re-wire callbacks without tearing down the hook or HID++.
        """
        with self._lock:
            self.cfg = load_config()
            self._current_profile = self.cfg.get("active_profile", "default")
            self.hook.reset_bindings()
            self._setup_hooks()
            self._emit_debug(f"reload_mappings profile={self._current_profile}")

    def set_enabled(self, enabled):
        self._enabled = bool(enabled)

    def set_ui_passthrough(self, enabled):
        if hasattr(self.hook, "set_ui_passthrough"):
            self.hook.set_ui_passthrough(enabled)

    def _emit_linux_permission_warning(self):
        report = linux_permission_report()
        log_message = linux_permission_log_message(report)
        if log_message:
            print(log_message)
        status_message = linux_permission_status_message(report)
        if status_message:
            self._emit_status(status_message)

    def start(self):
        self._emit_linux_permission_warning()
        self.hook.start()
        self._app_detector.start()
        # Temporary safety-net: keep the old delayed replay path until the
        # hid-ready transition path has proven out in the field.
        def _startup_replay_fallback():
            time.sleep(3)
            if not self.hid_features_ready:
                return
            self._request_saved_settings_replay(startup_fallback=True)
        threading.Thread(target=_startup_replay_fallback, daemon=True).start()

    def set_dpi_read_callback(self, cb):
        """Register a callback ``cb(dpi_value)`` invoked when DPI is read from device."""
        self._dpi_read_cb = cb

    def set_smart_shift_read_callback(self, cb):
        """Register a callback ``cb(state)`` invoked when Smart Shift is read."""
        self._smart_shift_read_cb = cb

    def stop(self):
        self._battery_poll_stop.set()
        if self._battery_poll_thread is not None:
            self._battery_poll_thread.join(timeout=5)
            self._battery_poll_thread = None
        self._app_detector.stop()
        self.hook.stop()
