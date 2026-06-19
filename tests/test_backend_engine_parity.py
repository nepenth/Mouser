"""Task A closure audit: Engine public HID++ API must have Backend exposure."""

import copy
import unittest
from unittest.mock import patch

from core.config import DEFAULT_CONFIG
from tests.test_backend import _FakeEngine, _ensure_qapp
from ui.backend import Backend

# Engine snake_case method -> Backend camelCase slot or @Property name
ENGINE_TO_BACKEND = {
    "read_backlight": "readBacklight",
    "set_backlight": "setBacklight",
    "read_fn_inversion": "readFnInversion",
    "set_fn_inversion": "setFnInversion",
    "has_backlight_control": "keyboardBacklightSupported",
    "has_fn_inversion_control": "keyboardFnInversionSupported",
    "set_report_rate": "setReportRate",
    "read_report_rate": "readReportRate",
    "read_onboard_profile": "readOnboardProfile",
    "switch_onboard_profile": "switchOnboardProfile",
    "read_device_name": "readDeviceName",
    "set_device_name": "setDeviceName",
    "read_device_friendly_name": "readDeviceFriendlyName",
    "set_device_friendly_name": "setDeviceFriendlyName",
    "set_led_state": "setLedState",
    "read_led_state": "readLedState",
    "read_device_mode": "readDeviceMode",
    "set_device_mode": "setDeviceMode",
    "read_wireless_power": "readWirelessPower",
    "set_wireless_power": "setWirelessPower",
    "read_wireless_channel": "readWirelessChannel",
    "set_wireless_channel": "setWirelessChannel",
    "read_sleep_timeout": "readSleepTimeout",
    "set_sleep_timeout": "setSleepTimeout",
    "read_wireless_status": "readWirelessStatus",
    "read_led_effect": "readLedEffect",
    "set_led_effect": "setLedEffect",
    "read_device_identity": "readDeviceIdentity",
    "read_device_type": "getDeviceType",
    "get_remaining_pairing_slots": "getRemainingPairingSlots",
    "get_force_sensing_buttons": "getForceSensingButtons",
    "read_power_management": "readPowerManagement",
    "set_power_management": "setPowerManagement",
    "set_litra_illumination": "setLitraIllumination",
    "read_litra_illumination": "readLitraIllumination",
    "read_smart_shift": "readSmartShift",
    "set_dpi": "setDpi",
    "set_smart_shift": "setSmartShift",
}


class BackendEngineParityTests(unittest.TestCase):
    def test_every_engine_hid_api_has_backend_surface(self):
        missing = []
        for engine_name, backend_name in ENGINE_TO_BACKEND.items():
            if not hasattr(Backend, backend_name):
                missing.append(f"{engine_name} -> {backend_name}")
        self.assertEqual(missing, [], f"Missing Backend surfaces: {missing}")

    def test_read_smart_shift_delegates(self):
        _ensure_qapp()
        fake = _FakeEngine()
        fake.read_smart_shift = lambda: {"mode": "ratchet", "enabled": False, "threshold": 25}
        with patch("ui.backend.load_config", return_value=copy.deepcopy(DEFAULT_CONFIG)):
            backend = Backend(engine=fake)
        self.assertEqual(
            backend.readSmartShift(),
            {"mode": "ratchet", "enabled": False, "threshold": 25},
        )


if __name__ == "__main__":
    unittest.main()