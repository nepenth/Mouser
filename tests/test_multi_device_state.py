import copy
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core.config import DEFAULT_CONFIG
from core.mouse_hook_types import HidRuntimeState


class _FakeMouseHook:
    def __init__(self):
        self.connected_device = None
        self.device_connected = False
        self._hid_gesture = None
        self.hid_runtime_state = None

    def set_debug_callback(self, cb):
        pass

    def set_gesture_callback(self, cb):
        pass

    def set_status_callback(self, cb):
        pass

    def set_connection_change_callback(self, cb):
        pass

    def configure_gestures(self, **kwargs):
        pass

    def block(self, event_type):
        pass

    def register(self, event_type, callback):
        pass

    def reset_bindings(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass


class _FakeAppDetector:
    def __init__(self, callback):
        pass

    def start(self):
        pass

    def stop(self):
        pass


def _mouse_device(**overrides):
    base = dict(
        key="mx_master_3",
        display_name="MX Master 3S",
        product_id=0xB023,
        dpi_min=200,
        dpi_max=8000,
        ui_layout="mx_master_3",
        supported_buttons=("middle",),
        capability_inventory=SimpleNamespace(
            device_identity=(("device_kind", "mouse"),),
            keyboard_device=False,
        ),
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _keyboard_device(**overrides):
    base = dict(
        key="mx_mechanical_mini",
        display_name="MX Mechanical Mini",
        product_id=0xB367,
        capability_inventory=SimpleNamespace(
            device_identity=(("device_kind", "keyboard"),),
            keyboard_device=True,
        ),
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class EngineMultiDeviceStateTests(unittest.TestCase):
    def _make_engine(self, cfg=None):
        from core.engine import Engine

        cfg = copy.deepcopy(cfg or DEFAULT_CONFIG)
        with (
            patch("core.engine.MouseHook", _FakeMouseHook),
            patch("core.engine.AppDetector", _FakeAppDetector),
            patch("core.engine.load_config", return_value=cfg),
            patch("core.engine.save_config"),
        ):
            return Engine()

    def test_active_mouse_device_returns_connected_device_when_mouse(self):
        engine = self._make_engine()
        device = _mouse_device()
        engine.hook.device_connected = True
        engine.hook.hid_runtime_state = HidRuntimeState(
            input_ready=True,
            hid_ready=True,
            connected_device=device,
        )

        self.assertIs(engine.active_mouse_device, device)
        self.assertIs(engine.connected_device, device)

    def test_active_mouse_device_returns_none_for_keyboard(self):
        engine = self._make_engine()
        device = _keyboard_device()
        engine.hook.device_connected = True
        engine.hook.hid_runtime_state = HidRuntimeState(
            input_ready=True,
            hid_ready=True,
            connected_device=device,
        )

        self.assertIsNone(engine.active_mouse_device)
        self.assertIs(engine.connected_device, device)

    def test_all_devices_includes_config_devices_and_connected(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg.setdefault("devices", {})["saved_keyboard"] = {
            "keyboard_middle_path": {
                "allow_host_backlight": True,
                "allow_fn_inversion": True,
                "allow_diversion_backlight": False,
            }
        }
        engine = self._make_engine(cfg=cfg)
        device = _mouse_device()
        engine.hook.device_connected = True
        engine.hook.hid_runtime_state = HidRuntimeState(
            input_ready=True,
            hid_ready=True,
            connected_device=device,
        )

        devices = engine.all_devices
        keys = {entry["key"] for entry in devices}
        self.assertIn("saved_keyboard", keys)
        self.assertIn("mx_master_3", keys)

        connected = [entry for entry in devices if entry["connected"]]
        self.assertEqual(len(connected), 1)
        self.assertEqual(connected[0]["key"], "mx_master_3")
        self.assertEqual(connected[0]["deviceKind"], "mouse")

    def test_selected_device_key_syncs_from_backend_setter(self):
        try:
            from PySide6.QtCore import QCoreApplication
            from ui.backend import Backend
        except ModuleNotFoundError:
            self.skipTest("PySide6 not available")

        app = QCoreApplication.instance()
        if app is None:
            app = QCoreApplication(sys.argv)

        engine = self._make_engine()
        backend = Backend(engine=engine)

        backend.setSelectedDeviceKey("saved_keyboard")
        self.assertEqual(engine.selected_device_key, "saved_keyboard")
        self.assertEqual(backend.selectedDeviceKey, "saved_keyboard")


class _FakeEngine:
    def __init__(
        self,
        *,
        device_connected=False,
        connected_device=None,
        active_mouse_device=None,
        selected_device_key="",
    ):
        self.device_connected = device_connected
        self.connected_device = connected_device
        self.active_mouse_device = active_mouse_device
        self.selected_device_key = selected_device_key
        self.hid_features_ready = False
        self.smart_shift_supported = False

    def set_profile_change_callback(self, cb):
        pass

    def set_dpi_read_callback(self, cb):
        pass

    def set_connection_change_callback(self, cb):
        pass

    def set_battery_callback(self, cb):
        pass

    def set_debug_callback(self, cb):
        pass

    def set_gesture_event_callback(self, cb):
        pass

    def set_status_callback(self, cb):
        pass

    def set_debug_enabled(self, enabled):
        pass

    def start(self):
        pass

    def stop(self):
        pass


class BackendMultiDeviceStateTests(unittest.TestCase):
    def _make_backend(self, *, engine=None, cfg=None):
        try:
            from PySide6.QtCore import QCoreApplication
            from ui.backend import Backend
        except ModuleNotFoundError:
            self.skipTest("PySide6 not available")

        app = QCoreApplication.instance()
        if app is None:
            app = QCoreApplication(sys.argv)

        backend = Backend(engine=engine)
        if cfg is not None:
            backend._cfg = copy.deepcopy(cfg)
            backend._sync_connected_devices_list()
        return backend

    def test_active_mouse_device_key_matches_connected_mouse(self):
        device = _mouse_device()
        engine = _FakeEngine(
            device_connected=True,
            connected_device=device,
            active_mouse_device=device,
        )
        backend = self._make_backend(engine=engine)
        backend._mouse_connected = True
        backend._connected_device_key = "mx_master_3"
        backend._sync_connected_devices_list()

        self.assertEqual(backend.activeMouseDeviceKey, "mx_master_3")
        self.assertEqual(backend.connectedDeviceKey, "mx_master_3")

    def test_active_mouse_device_key_empty_for_keyboard(self):
        device = _keyboard_device()
        engine = _FakeEngine(
            device_connected=True,
            connected_device=device,
            active_mouse_device=None,
        )
        backend = self._make_backend(engine=engine)
        backend._mouse_connected = True
        backend._connected_device_key = "mx_mechanical_mini"
        backend._sync_connected_devices_list()

        self.assertEqual(backend.activeMouseDeviceKey, "")
        self.assertEqual(backend.connectedDeviceKey, "mx_mechanical_mini")