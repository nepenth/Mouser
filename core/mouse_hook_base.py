"""
Shared mouse hook behavior used by platform implementations.
"""

import queue
import time

try:
    from core.hid_gesture import HidGestureListener
except Exception:
    HidGestureListener = None

from core.mouse_hook_types import HidRuntimeState, MouseEvent, format_debug_details
from core.config import get_keyboard_middle_path_settings


class BaseMouseHook:
    def __init__(self):
        self._callbacks = {}
        self._blocked_events = set()
        self._debug_callback = None
        self._gesture_callback = None
        self._status_callback = None
        self.debug_mode = False
        self.invert_vscroll = False
        self.invert_hscroll = False
        self._gesture_active = False
        self._hid_gesture = None
        self._device_connected = False
        self._connection_change_cb = None
        self.divert_mode_shift = False
        self.divert_dpi_switch = False
        self._gesture_direction_enabled = False
        self._gesture_threshold = 50.0
        self._gesture_deadzone = 40.0
        self._gesture_timeout_ms = 3000
        self._gesture_cooldown_ms = 500
        self._gesture_tracking = False
        self._gesture_triggered = False
        self._gesture_started_at = 0.0
        self._gesture_last_move_at = 0.0
        self._gesture_delta_x = 0.0
        self._gesture_delta_y = 0.0
        self._gesture_cooldown_until = 0.0
        self._gesture_input_source = None
        self._connected_device = None
        self._dispatch_queue = None

    def _init_dispatch_queue(self, maxsize=0):
        """Initialize dispatch queue storage for subclasses with event threads."""
        self._dispatch_queue = queue.Queue(maxsize=max(0, int(maxsize)))

    def _enqueue_dispatch_event(self, event):
        """Best-effort enqueue that bounds memory when queue has a max size."""
        q = self._dispatch_queue
        if q is None:
            return
        if q.maxsize <= 0:
            q.put(event)
            return
        try:
            q.put_nowait(event)
            return
        except queue.Full:
            pass
        try:
            q.get_nowait()
        except queue.Empty:
            pass
        try:
            q.put_nowait(event)
        except queue.Full:
            self._emit_debug(f"Dropped event due to full dispatch queue: {event.event_type}")

    def register(self, event_type, callback):
        self._callbacks.setdefault(event_type, []).append(callback)

    def block(self, event_type):
        self._blocked_events.add(event_type)

    def unblock(self, event_type):
        self._blocked_events.discard(event_type)

    def reset_bindings(self):
        self._callbacks.clear()
        self._blocked_events.clear()

    def configure_gestures(
        self,
        enabled=False,
        threshold=50,
        deadzone=40,
        timeout_ms=3000,
        cooldown_ms=500,
    ):
        self._gesture_direction_enabled = bool(enabled)
        self._gesture_threshold = float(max(5, threshold))
        self._gesture_deadzone = float(max(0, deadzone))
        self._gesture_timeout_ms = max(250, int(timeout_ms))
        self._gesture_cooldown_ms = max(0, int(cooldown_ms))
        if not self._gesture_direction_enabled:
            self._gesture_tracking = False
            self._gesture_triggered = False
            self._gesture_input_source = None

    def set_connection_change_callback(self, cb):
        self._connection_change_cb = cb

    @property
    def device_connected(self):
        return self._device_connected

    @property
    def connected_device(self):
        return self._connected_device

    @property
    def hid_runtime_state(self):
        hg = getattr(self, "_hid_gesture", None)
        hid_device = getattr(hg, "connected_device", None) if hg else None
        return HidRuntimeState(
            input_ready=bool(self._device_connected),
            hid_ready=hid_device is not None,
            connected_device=self._connected_device,
        )

    def dump_device_info(self):
        hg = getattr(self, "_hid_gesture", None)
        if hg and hasattr(hg, "dump_device_info"):
            return hg.dump_device_info()
        return None

    def _set_device_connected(self, connected):
        if connected == self._device_connected:
            return
        self._device_connected = connected
        state = "Connected" if connected else "Disconnected"
        print(f"[MouseHook] Device {state}")
        if self._connection_change_cb:
            try:
                self._connection_change_cb(connected)
            except Exception:
                pass

    def set_debug_callback(self, callback):
        self._debug_callback = callback

    def set_gesture_callback(self, callback):
        self._gesture_callback = callback

    def set_status_callback(self, callback):
        self._status_callback = callback

    def _emit_debug(self, message):
        if self.debug_mode and self._debug_callback:
            try:
                self._debug_callback(message)
            except Exception:
                pass

    def _emit_status(self, message):
        if self._status_callback:
            try:
                self._status_callback(message)
            except Exception:
                pass

    def _emit_gesture_event(self, event):
        if self.debug_mode and self._gesture_callback:
            try:
                self._gesture_callback(event)
            except Exception:
                pass

    def _dispatch(self, event):
        callbacks = self._callbacks.get(event.event_type, [])
        self._emit_debug(
            f"Dispatch {event.event_type}"
            f"{format_debug_details(event.raw_data)} callbacks={len(callbacks)}"
        )
        if event.event_type.startswith("gesture_"):
            self._emit_gesture_event(
                {
                    "type": "dispatch",
                    "event_name": event.event_type,
                    "callbacks": len(callbacks),
                }
            )
        if not callbacks:
            self._emit_debug(f"No mapped action for {event.event_type}")
            if event.event_type.startswith("gesture_"):
                self._emit_gesture_event(
                    {
                        "type": "unmapped",
                        "event_name": event.event_type,
                    }
                )
        for callback in callbacks:
            try:
                callback(event)
            except Exception as exc:
                print(f"[MouseHook] callback error: {exc}")

    def _hid_gesture_available(self):
        return self._hid_gesture is not None and self._device_connected

    def _gesture_cooldown_active(self):
        return time.monotonic() < self._gesture_cooldown_until

    def _start_gesture_tracking(self):
        self._gesture_tracking = self._gesture_direction_enabled
        self._gesture_started_at = time.monotonic()
        self._gesture_last_move_at = self._gesture_started_at
        self._gesture_delta_x = 0.0
        self._gesture_delta_y = 0.0
        self._gesture_input_source = None

    def _finish_gesture_tracking(self):
        self._gesture_tracking = False
        self._gesture_started_at = 0.0
        self._gesture_last_move_at = 0.0
        self._gesture_delta_x = 0.0
        self._gesture_delta_y = 0.0
        self._gesture_input_source = None

    def _detect_gesture_event(self):
        delta_x = self._gesture_delta_x
        delta_y = self._gesture_delta_y

        abs_x = abs(delta_x)
        abs_y = abs(delta_y)
        dominant = max(abs_x, abs_y)
        if dominant < self._gesture_threshold:
            return None

        cross_limit = max(self._gesture_deadzone, dominant * 0.35)

        if abs_x > abs_y:
            if abs_y > cross_limit:
                return None
            if delta_x > 0:
                return MouseEvent.GESTURE_SWIPE_RIGHT
            return MouseEvent.GESTURE_SWIPE_LEFT

        if abs_x > cross_limit:
            return None
        if delta_y > 0:
            return MouseEvent.GESTURE_SWIPE_DOWN
        return MouseEvent.GESTURE_SWIPE_UP

    def _build_extra_diverts(self, cfg=None, current_device=None):
        extra = {}
        if self.divert_mode_shift:
            extra[0x00C4] = {
                "on_down": self._on_hid_mode_shift_down,
                "on_up": self._on_hid_mode_shift_up,
            }
        if self.divert_dpi_switch:
            extra[0x00FD] = {
                "on_down": self._on_hid_dpi_switch_down,
                "on_up": self._on_hid_dpi_switch_up,
            }

        # 007.2: Conditional, opt-in diversion for the two safest MX Mechanical Mini backlight keys
        # (Backlight Up / Backlight Down). Only active when the user has explicitly enabled
        # allow_diversion_backlight for this specific device.
        try:
            cfg = cfg or getattr(self, "cfg", None)
            dev = current_device or getattr(self, "_hid_device_info", None) or getattr(getattr(self, "_hid_gesture", None), "connected_device", None)

            if dev and cfg:
                name = getattr(dev, "name", "") or ""
                pid = getattr(dev, "product_id", 0) or 0
                is_mx_mechanical_mini = ("MX Mechanical Mini" in name) or (pid in (0xB369, 0xB36B))

                if is_mx_mechanical_mini:
                    device_key = getattr(dev, "key", None) or str(pid)
                    kmp = get_keyboard_middle_path_settings(cfg, device_key)
                    if kmp.get("allow_diversion_backlight", False):
                        # The two safest backlight CIDs on MX Mechanical Mini (REPROG controls)
                        # These are the ones previously identified as the lowest-risk to divert.
                        BACKLIGHT_UP_CID = 0x00C5
                        BACKLIGHT_DOWN_CID = 0x00C6

                        extra[BACKLIGHT_UP_CID] = {
                            "on_down": self._on_hid_keyboard_backlight_up_down,
                            "on_up": self._on_hid_keyboard_backlight_up_up,
                        }
                        extra[BACKLIGHT_DOWN_CID] = {
                            "on_down": self._on_hid_keyboard_backlight_down_down,
                            "on_up": self._on_hid_keyboard_backlight_down_up,
                        }
                        print(f"[MouseHook] Enabling opt-in backlight key diversion for device {device_key} (flag allow_diversion_backlight=True)")
                    else:
                        print(f"[MouseHook] Backlight key diversion skipped for device {device_key} (flag allow_diversion_backlight=False or not set)")
        except Exception as e:
            print(f"[MouseHook] Error building keyboard backlight diversion: {e}")

        return extra

    # Placeholder handlers for the two MX Mechanical Mini backlight keys (007.2 skeleton)
    # These will later be wired to real mappable events in 007.3+.
    def _on_hid_keyboard_backlight_up_down(self):
        print("[MouseHook] Backlight Up key (diverted, opt-in) pressed")
        # Future: dispatch a recognizable event the mapping system can use

    def _on_hid_keyboard_backlight_up_up(self):
        print("[MouseHook] Backlight Up key (diverted, opt-in) released")

    def _on_hid_keyboard_backlight_down_down(self):
        print("[MouseHook] Backlight Down key (diverted, opt-in) pressed")

    def _on_hid_keyboard_backlight_down_up(self):
        print("[MouseHook] Backlight Down key (diverted, opt-in) released")

    def _start_hid_listener(self):
        platform_module = getattr(self.__class__, "_platform_module", None)
        listener_cls = getattr(platform_module, "HidGestureListener", HidGestureListener)
        if listener_cls is None:
            return None
        # Pass cfg and current device so 007.2+ can make per-device diversion decisions
        cfg = getattr(self, "cfg", None)
        dev = getattr(self, "_hid_device_info", None) or getattr(getattr(self, "_hid_gesture", None), "connected_device", None)

        listener = listener_cls(
            on_down=self._on_hid_gesture_down,
            on_up=self._on_hid_gesture_up,
            on_move=self._on_hid_gesture_move,
            on_connect=self._on_hid_connect,
            on_disconnect=self._on_hid_disconnect,
            extra_diverts=self._build_extra_diverts(cfg=cfg, current_device=dev),
        )
        self._hid_gesture = listener
        if not listener.start():
            self._hid_gesture = None
        return self._hid_gesture

    def _stop_hid_listener(self):
        if self._hid_gesture:
            self._hid_gesture.stop()
            self._hid_gesture = None

    def _on_hid_connect(self):
        self._connected_device = (
            self._hid_gesture.connected_device if self._hid_gesture else None
        )
        self._set_device_connected(True)

    def _on_hid_disconnect(self):
        self._connected_device = None
        self._set_device_connected(False)

    def _on_hid_gesture_down(self):
        self._dispatch(MouseEvent(MouseEvent.GESTURE_DOWN))

    def _on_hid_gesture_up(self):
        self._dispatch(MouseEvent(MouseEvent.GESTURE_UP))

    def _on_hid_gesture_move(self, dx, dy):
        self._accumulate_gesture_delta(dx, dy, "hid_rawxy")

    def _on_hid_mode_shift_down(self):
        self._dispatch(MouseEvent(MouseEvent.MODE_SHIFT_DOWN))

    def _on_hid_mode_shift_up(self):
        self._dispatch(MouseEvent(MouseEvent.MODE_SHIFT_UP))

    def _on_hid_dpi_switch_down(self):
        self._dispatch(MouseEvent(MouseEvent.DPI_SWITCH_DOWN))

    def _on_hid_dpi_switch_up(self):
        self._dispatch(MouseEvent(MouseEvent.DPI_SWITCH_UP))
