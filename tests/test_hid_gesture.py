import importlib
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from core import hid_gesture
from core.config import DEFAULT_CONFIG


class HidModuleImportTests(unittest.TestCase):
    def tearDown(self):
        importlib.reload(hid_gesture)

    def test_linux_prefers_hidraw_module_when_available(self):
        fake_hidraw = SimpleNamespace(device=object, enumerate=lambda *_args: [])
        fake_hid = SimpleNamespace(device=object, enumerate=lambda *_args: [])

        with (
            patch.object(sys, "platform", "linux"),
            patch.dict(sys.modules, {"hidraw": fake_hidraw, "hid": fake_hid}),
        ):
            module = importlib.reload(hid_gesture)

        self.assertTrue(module.HIDAPI_OK)
        self.assertIs(module._hid, fake_hidraw)
        self.assertEqual(module._HID_MODULE_NAME, "hidraw")

    def test_linux_falls_back_to_hid_when_hidraw_module_is_absent(self):
        fake_hid = SimpleNamespace(device=object, enumerate=lambda *_args: [])

        with (
            patch.object(sys, "platform", "linux"),
            patch.dict(sys.modules, {"hidraw": None, "hid": fake_hid}),
        ):
            module = importlib.reload(hid_gesture)

        self.assertTrue(module.HIDAPI_OK)
        self.assertIs(module._hid, fake_hid)
        self.assertEqual(module._HID_MODULE_NAME, "hid")


class HidLinuxDiagnosticsTests(unittest.TestCase):
    def test_linux_logitech_hidraw_nodes_reads_sysfs_uevent(self):
        with tempfile.TemporaryDirectory() as tmp:
            node_dir = os.path.join(tmp, "hidraw3", "device")
            os.makedirs(node_dir)
            with open(os.path.join(node_dir, "uevent"), "w", encoding="utf-8") as fh:
                fh.write("HID_ID=0005:0000046D:0000B034\n")
                fh.write("HID_NAME=MX Master 3S\n")

            with patch.object(sys, "platform", "linux"):
                nodes = hid_gesture._linux_logitech_hidraw_nodes(base=tmp)

        self.assertEqual(nodes, ["hidraw3 PID=0xB034 product=MX Master 3S"])

    def test_summarize_hid_infos_includes_candidate_metadata(self):
        summary = hid_gesture._summarize_hid_infos([
            {
                "product_id": 0xB034,
                "usage_page": 0x0000,
                "usage": 0x0001,
                "transport": "Bluetooth Low Energy",
                "product_string": "MX Master 3S",
            }
        ])

        self.assertIn("PID=0xB034", summary)
        self.assertIn("UP=0x0000", summary)
        self.assertIn("product=MX Master 3S", summary)

    def test_format_linux_device_access_includes_path_permissions_and_access(self):
        with tempfile.NamedTemporaryFile() as fh:
            summary = hid_gesture._format_linux_device_access(fh.name.encode())

        self.assertIn("path=", summary)
        self.assertIn("mode=", summary)
        self.assertIn("owner=", summary)
        self.assertIn("group=", summary)
        self.assertIn("access=read:", summary)


class HidBackendPreferenceTests(unittest.TestCase):
    def test_default_backend_uses_auto_on_macos(self):
        self.assertEqual(hid_gesture._default_backend_preference("darwin"), "auto")

    def test_default_backend_uses_auto_elsewhere(self):
        self.assertEqual(hid_gesture._default_backend_preference("win32"), "auto")
        self.assertEqual(hid_gesture._default_backend_preference("linux"), "auto")


class GestureCandidateSelectionTests(unittest.TestCase):
    def test_choose_gesture_candidates_prefers_known_device_cids(self):
        listener = hid_gesture.HidGestureListener()
        device_spec = hid_gesture.resolve_device(product_id=0xB023)

        candidates = listener._choose_gesture_candidates(
            [
                {"cid": 0x00D7, "flags": 0x03B0, "mapping_flags": 0x0051},
                {"cid": 0x00C3, "flags": 0x0130, "mapping_flags": 0x0011},
            ],
            device_spec=device_spec,
        )

        self.assertEqual(candidates[:2], [0x00C3, 0x00D7])

    def test_choose_gesture_candidates_uses_capability_heuristic(self):
        listener = hid_gesture.HidGestureListener()

        candidates = listener._choose_gesture_candidates(
            [
                {"cid": 0x00A0, "flags": 0x0030, "mapping_flags": 0x0001},
                {"cid": 0x00F1, "flags": 0x01B0, "mapping_flags": 0x0011},
            ],
        )

        self.assertEqual(candidates[0], 0x00F1)

    def test_choose_gesture_candidates_falls_back_to_defaults(self):
        listener = hid_gesture.HidGestureListener()

        self.assertEqual(
            listener._choose_gesture_candidates([]),
            list(hid_gesture.DEFAULT_GESTURE_CIDS),
        )


class DeviceInfoDumpTests(unittest.TestCase):
    def test_dump_device_info_includes_runtime_capability_inventory(self):
        listener = hid_gesture.HidGestureListener()
        controls = [
            {
                "index": 0,
                "cid": 0x00D0,
                "task": 0x00AD,
                "flags": 0x0171,
                "mapped_to": 0x00D0,
                "mapping_flags": 0x0000,
            },
            {
                "index": 1,
                "cid": 0x005B,
                "task": 0x003F,
                "flags": 0x0171,
                "mapped_to": 0x005B,
                "mapping_flags": 0x0000,
            },
        ]
        listener._feat_idx = 0x0B
        listener._battery_idx = 0x08
        listener._battery_feature_id = hid_gesture.FEAT_BATTERY_STATUS
        listener._gesture_candidates = [0x00D0]
        listener._connected_device_info = hid_gesture.build_connected_device_info(
            product_id=0xB015,
            product_name="M720_Triathlon",
            reprog_controls=controls,
            gesture_cids=(0x00D0,),
            active_gesture_cid=0x00D0,
            gesture_rawxy_enabled=True,
            discovered_features=listener._discovered_feature_ids(),
        )
        listener._last_controls = controls

        dump = listener.dump_device_info()

        self.assertEqual(dump["device_key"], "m720_triathlon")
        self.assertIn("capability_inventory", dump)
        self.assertEqual(
            dump["capability_inventory"]["active_gesture_cid"],
            "0x00D0",
        )
        self.assertTrue(dump["capability_inventory"]["gesture_directions"])
        self.assertEqual(dump["capability_inventory"]["hscroll_cids"], ["0x005B"])
        self.assertTrue(dump["capability_inventory"]["battery"])


class BatteryParseTests(unittest.TestCase):
    def test_parse_battery_response_returns_normalized_level(self):
        listener = hid_gesture.HidGestureListener()
        parsed = listener._parse_battery_response(bytes([75]))
        self.assertEqual(parsed, {"level": 75})

    def test_parse_battery_response_rejects_out_of_range(self):
        listener = hid_gesture.HidGestureListener()
        self.assertIsNone(listener._parse_battery_response(bytes([101])))
        self.assertIsNone(listener._parse_battery_response(b""))


class _FakeHidDevice:
    def __init__(self):
        self.open_path = Mock()
        self.set_nonblocking = Mock()
        self.close = Mock()


class HidEnumerationFallbackTests(unittest.TestCase):
    @staticmethod
    def _printed_messages(print_mock):
        return [
            " ".join(str(arg) for arg in call.args)
            for call in print_mock.call_args_list
        ]

    def test_try_connect_accepts_known_device_without_usage_metadata(self):
        listener = hid_gesture.HidGestureListener()
        info = {
            "product_id": 0xB034,
            "usage_page": 0x0000,
            "usage": 0x0000,
            "transport": "Bluetooth Low Energy",
            "product_string": "MX Master 3S",
            "path": b"/dev/hidraw-test",
        }
        fake_dev = _FakeHidDevice()

        def fake_find_feature(feature_id):
            if feature_id == hid_gesture.FEAT_REPROG_V4:
                return 0x10
            return None

        with (
            patch.object(hid_gesture, "HIDAPI_OK", True),
            patch.object(hid_gesture, "_BACKEND_PREFERENCE", "hidapi"),
            patch.object(hid_gesture, "_HID_API_STYLE", "hidapi"),
            patch.object(
                hid_gesture,
                "_hid",
                SimpleNamespace(
                    enumerate=lambda vid, pid: [info],
                    device=lambda: fake_dev,
                ),
                create=True,
            ),
            patch.object(listener, "_find_feature", side_effect=fake_find_feature),
            patch.object(listener, "_discover_reprog_controls", return_value=[]),
            patch.object(listener, "_divert", return_value=True),
            patch.object(listener, "_divert_extras"),
            patch("builtins.print") as print_mock,
        ):
            self.assertTrue(listener._try_connect())

        messages = self._printed_messages(print_mock)
        self.assertTrue(
            any(
                "Accepting known Logitech device without vendor usage metadata"
                in message
                for message in messages
            )
        )
        self.assertEqual(listener.connected_device.display_name, "MX Master 3S")

    def test_vendor_hid_infos_logs_when_logitech_interfaces_are_filtered_out(self):
        info = {
            "product_id": 0x1234,
            "usage_page": 0x0000,
            "usage": 0x0000,
            "transport": "Bluetooth Low Energy",
            "product_string": "Unknown Logitech",
            "path": b"/dev/hidraw-test",
        }

        with (
            patch.object(hid_gesture, "HIDAPI_OK", True),
            patch.object(hid_gesture, "_BACKEND_PREFERENCE", "hidapi"),
            patch.object(
                hid_gesture,
                "_hid",
                SimpleNamespace(enumerate=lambda vid, pid: [info]),
                create=True,
            ),
            patch("builtins.print") as print_mock,
        ):
            infos = hid_gesture.HidGestureListener._vendor_hid_infos()

        self.assertEqual(infos, [])
        messages = self._printed_messages(print_mock)
        self.assertTrue(
            any(
                "hidapi found Logitech interfaces, but none matched vendor "
                "usage metadata or known-device fallback"
                in message
                for message in messages
            )
        )


class HidDiscoveryDiagnosticsTests(unittest.TestCase):
    def _make_listener(self):
        listener = hid_gesture.HidGestureListener()
        info = {
            "product_id": 0xB023,
            "usage_page": 0xFF00,
            "usage": 0x0001,
            "transport": "Bluetooth Low Energy",
            "source": "hidapi-enumerate",
            "product_string": "MX Master 3",
            "path": b"/dev/hidraw-test",
        }
        return listener, info

    @staticmethod
    def _printed_messages(print_mock):
        return [
            " ".join(str(arg) for arg in call.args)
            for call in print_mock.call_args_list
        ]

    @staticmethod
    def _is_missing_reprog_diag(message):
        return (
            "Opened candidate but REPROG_V4 was not found "
            "on tested devIdx values"
        ) in message

    def test_try_connect_logs_missing_reprog_when_open_succeeds_for_all_dev_indices(self):
        listener, info = self._make_listener()
        fake_dev = _FakeHidDevice()

        with (
            patch.object(listener, "_vendor_hid_infos", return_value=[info]),
            patch.object(listener, "_find_feature", return_value=None),
            patch.object(hid_gesture, "HIDAPI_OK", True),
            patch.object(hid_gesture, "_BACKEND_PREFERENCE", "hidapi"),
            patch.object(hid_gesture, "_HID_API_STYLE", "hidapi"),
            patch.object(
                hid_gesture,
                "_hid",
                SimpleNamespace(device=lambda: fake_dev),
                create=True,
            ),
            patch("builtins.print") as print_mock,
        ):
            self.assertFalse(listener._try_connect())

        messages = self._printed_messages(print_mock)
        self.assertTrue(
            any("Opened PID=0xB023 via hidapi" in message for message in messages)
        )
        self.assertTrue(
            any(self._is_missing_reprog_diag(message) for message in messages)
        )
        fake_dev.close.assert_called_once_with()

    def test_try_connect_logs_linux_hid_path_access_before_open(self):
        listener, info = self._make_listener()
        fake_dev = _FakeHidDevice()
        fake_dev.open_path.side_effect = OSError("open failed")

        with tempfile.NamedTemporaryFile() as fh:
            info = dict(info, path=fh.name.encode())
            with (
                patch.object(sys, "platform", "linux"),
                patch.object(listener, "_vendor_hid_infos", return_value=[info]),
                patch.object(hid_gesture, "HIDAPI_OK", True),
                patch.object(hid_gesture, "_BACKEND_PREFERENCE", "hidapi"),
                patch.object(hid_gesture, "_HID_API_STYLE", "hidapi"),
                patch.object(
                    hid_gesture,
                    "_hid",
                    SimpleNamespace(device=lambda: fake_dev),
                    create=True,
                ),
                patch("builtins.print") as print_mock,
            ):
                hid_gesture._LOG_ONCE_KEYS.clear()
                self.assertFalse(listener._try_connect())

        messages = self._printed_messages(print_mock)
        self.assertTrue(
            any("HID path access before open:" in message for message in messages)
        )
        self.assertTrue(any("access=read:" in message for message in messages))

    def test_try_connect_success_path_keeps_existing_reprog_discovery_diagnostics(self):
        listener, info = self._make_listener()
        fake_dev = _FakeHidDevice()

        def fake_find_feature(feature_id):
            if feature_id == hid_gesture.FEAT_REPROG_V4:
                return 0x10
            return None

        with (
            patch.object(listener, "_vendor_hid_infos", return_value=[info]),
            patch.object(listener, "_find_feature", side_effect=fake_find_feature),
            patch.object(listener, "_discover_reprog_controls", return_value=[]),
            patch.object(listener, "_divert", return_value=True),
            patch.object(listener, "_divert_extras"),
            patch.object(hid_gesture, "HIDAPI_OK", True),
            patch.object(hid_gesture, "_BACKEND_PREFERENCE", "hidapi"),
            patch.object(hid_gesture, "_HID_API_STYLE", "hidapi"),
            patch.object(
                hid_gesture,
                "_hid",
                SimpleNamespace(device=lambda: fake_dev),
                create=True,
            ),
            patch("builtins.print") as print_mock,
        ):
            self.assertTrue(listener._try_connect())

        messages = self._printed_messages(print_mock)
        self.assertTrue(
            any("Opened PID=0xB023 via hidapi" in message for message in messages)
        )
        self.assertTrue(
            any("Found REPROG_V4 @0x10" in message for message in messages)
        )
        self.assertFalse(
            any(self._is_missing_reprog_diag(message) for message in messages)
        )
        fake_dev.close.assert_not_called()

    def test_try_connect_rearms_extra_diverts_on_reconnect(self):
        listener = hid_gesture.HidGestureListener(
            extra_diverts={
                0x00C4: {"on_down": Mock(), "on_up": Mock()},
            }
        )
        info = {
            "product_id": 0xB023,
            "usage_page": 0xFF00,
            "usage": 0x0001,
            "transport": "Bluetooth Low Energy",
            "source": "hidapi-enumerate",
            "product_string": "MX Master 3",
            "path": b"/dev/hidraw-test",
        }
        fake_devs = [_FakeHidDevice(), _FakeHidDevice()]

        def fake_find_feature(feature_id):
            if feature_id == hid_gesture.FEAT_REPROG_V4:
                return 0x10
            return None

        with (
            patch.object(listener, "_vendor_hid_infos", return_value=[info]),
            patch.object(listener, "_find_feature", side_effect=fake_find_feature),
            patch.object(listener, "_discover_reprog_controls", return_value=[]),
            patch.object(listener, "_divert", return_value=True),
            patch.object(listener, "_divert_extras") as divert_extras_mock,
            patch.object(hid_gesture, "HIDAPI_OK", True),
            patch.object(hid_gesture, "_BACKEND_PREFERENCE", "hidapi"),
            patch.object(hid_gesture, "_HID_API_STYLE", "hidapi"),
            patch.object(
                hid_gesture,
                "_hid",
                SimpleNamespace(device=lambda: fake_devs.pop(0)),
                create=True,
            ),
        ):
            self.assertTrue(listener._try_connect())
            listener._dev = None
            self.assertTrue(listener._try_connect())

        self.assertEqual(divert_extras_mock.call_count, 2)
        self.assertIn(0x00C4, listener._extra_diverts)
        self.assertFalse(listener._extra_diverts[0x00C4]["held"])


class HidRequestTransportFailureTests(unittest.TestCase):
    def test_request_raises_ioerror_on_tx_failure_during_active_session(self):
        listener = hid_gesture.HidGestureListener()
        listener._connected = True

        with patch.object(listener, "_tx", side_effect=OSError("tx boom")):
            with self.assertRaises(IOError):
                listener._request(0x0E, 0, [])

    def test_request_raises_ioerror_on_rx_failure_during_active_session(self):
        listener = hid_gesture.HidGestureListener()
        listener._connected = True

        with (
            patch.object(listener, "_tx"),
            patch.object(listener, "_rx", side_effect=OSError("rx boom")),
        ):
            with self.assertRaises(IOError):
                listener._request(0x0E, 0, [])

    def test_request_returns_none_on_tx_failure_during_discovery(self):
        listener = hid_gesture.HidGestureListener()

        with patch.object(listener, "_tx", side_effect=OSError("tx boom")):
            self.assertIsNone(listener._request(0x0E, 0, []))

    def test_request_returns_none_on_rx_failure_during_discovery(self):
        listener = hid_gesture.HidGestureListener()

        with (
            patch.object(listener, "_tx"),
            patch.object(listener, "_rx", side_effect=OSError("rx boom")),
        ):
            self.assertIsNone(listener._request(0x0E, 0, []))

    def test_request_timeout_still_increments_timeout_counter(self):
        listener = hid_gesture.HidGestureListener()

        with (
            patch.object(listener, "_tx"),
            patch.object(listener, "_rx", return_value=None),
        ):
            self.assertIsNone(listener._request(0x0E, 0, [], timeout_ms=0))

        self.assertEqual(listener._consecutive_request_timeouts, 1)


class HidBoltReceiverTests(unittest.TestCase):
    """Tests for Logi Bolt receiver support."""

    def test_divert_failure_continues_to_next_receiver_slot(self):
        """When divert fails on one slot (e.g. keyboard), the loop
        continues and connects to the mouse on a later slot."""
        listener = hid_gesture.HidGestureListener()
        info = {
            "product_id": 0xC548,
            "usage_page": 0xFF00,
            "usage": 0x0001,
            "source": "hidapi-enumerate",
            "product_string": "USB Receiver",
            "path": b"/dev/hidraw-test",
        }
        fake_dev = _FakeHidDevice()
        divert_call_count = [0]

        def fake_find_feature(feature_id):
            if feature_id == hid_gesture.FEAT_REPROG_V4:
                return 0x09
            return None

        def fake_divert():
            divert_call_count[0] += 1
            # First call fails (keyboard), second succeeds (mouse)
            return divert_call_count[0] >= 2

        with (
            patch.object(listener, "_vendor_hid_infos", return_value=[info]),
            patch.object(listener, "_find_feature", side_effect=fake_find_feature),
            patch.object(listener, "_discover_reprog_controls", return_value=[]),
            patch.object(listener, "_divert", side_effect=fake_divert),
            patch.object(listener, "_divert_extras"),
            patch.object(hid_gesture, "HIDAPI_OK", True),
            patch.object(hid_gesture, "_BACKEND_PREFERENCE", "hidapi"),
            patch.object(hid_gesture, "_HID_API_STYLE", "hidapi"),
            patch.object(
                hid_gesture,
                "_hid",
                SimpleNamespace(device=lambda: fake_dev),
                create=True,
            ),
            patch("builtins.print"),
        ):
            self.assertTrue(listener._try_connect())
            self.assertEqual(divert_call_count[0], 2)

    def test_candidates_sorted_direct_devices_before_receivers(self):
        """Bluetooth devices should be tried before USB receivers."""
        listener = hid_gesture.HidGestureListener()
        infos = [
            {"product_string": "USB Receiver", "product_id": 0xC548,
             "usage_page": 0xFF00, "usage": 1, "source": "hidapi"},
            {"product_string": "MX Master 3S", "product_id": 0xB034,
             "usage_page": 0xFF43, "usage": 1, "source": "hidapi"},
            {"product_string": "USB Receiver", "product_id": 0xC548,
             "usage_page": 0xFF00, "usage": 2, "source": "hidapi"},
        ]

        with patch.object(listener, "_vendor_hid_infos", return_value=infos):
            # _try_connect sorts infos in place before iterating
            with (
                patch.object(listener, "_find_feature", return_value=None),
                patch("builtins.print"),
            ):
                listener._try_connect()

        # After sorting, direct device should be first
        self.assertEqual(infos[0]["product_string"], "MX Master 3S")

    def test_transport_label_bluetooth_for_direct_connection(self):
        """devIdx 0xFF should produce 'Bluetooth' transport."""
        listener = hid_gesture.HidGestureListener()
        info = {
            "product_id": 0xB034,
            "usage_page": 0xFF00,
            "usage": 0x0001,
            "source": "hidapi-enumerate",
            "product_string": "MX Master 3S",
            "path": b"/dev/hidraw-test",
        }
        fake_dev = _FakeHidDevice()

        def fake_find_feature(feature_id):
            if feature_id == hid_gesture.FEAT_REPROG_V4:
                return 0x09
            return None

        with (
            patch.object(listener, "_vendor_hid_infos", return_value=[info]),
            patch.object(listener, "_find_feature", side_effect=fake_find_feature),
            patch.object(listener, "_discover_reprog_controls", return_value=[]),
            patch.object(listener, "_divert", return_value=True),
            patch.object(listener, "_divert_extras"),
            patch.object(hid_gesture, "HIDAPI_OK", True),
            patch.object(hid_gesture, "_BACKEND_PREFERENCE", "hidapi"),
            patch.object(hid_gesture, "_HID_API_STYLE", "hidapi"),
            patch.object(
                hid_gesture,
                "_hid",
                SimpleNamespace(device=lambda: fake_dev),
                create=True,
            ),
            patch("builtins.print"),
        ):
            self.assertTrue(listener._try_connect())

        # devIdx 0xFF (first tried) = Bluetooth
        self.assertEqual(listener.connected_device.transport, "Bluetooth")

    def test_try_connect_applies_runtime_supported_buttons(self):
        listener = hid_gesture.HidGestureListener()
        info = {
            "product_id": 0xB034,
            "usage_page": 0xFF00,
            "usage": 0x0001,
            "source": "hidapi-enumerate",
            "product_string": "MX Master 3S",
            "path": b"/dev/hidraw-test",
        }
        controls = [
            {"cid": 0x0052, "flags": 0x0030, "mapping_flags": 0x0001},
            {"cid": 0x0053, "flags": 0x0030, "mapping_flags": 0x0001},
            {"cid": 0x0056, "flags": 0x0030, "mapping_flags": 0x0001},
            {"cid": 0x00C3, "flags": 0x0130, "mapping_flags": 0x0011},
        ]
        fake_dev = _FakeHidDevice()

        def fake_find_feature(feature_id):
            if feature_id == hid_gesture.FEAT_REPROG_V4:
                return 0x09
            return None

        with (
            patch.object(listener, "_vendor_hid_infos", return_value=[info]),
            patch.object(listener, "_find_feature", side_effect=fake_find_feature),
            patch.object(listener, "_discover_reprog_controls", return_value=controls),
            patch.object(listener, "_divert", return_value=True),
            patch.object(listener, "_divert_extras"),
            patch.object(hid_gesture, "HIDAPI_OK", True),
            patch.object(hid_gesture, "_BACKEND_PREFERENCE", "hidapi"),
            patch.object(hid_gesture, "_HID_API_STYLE", "hidapi"),
            patch.object(
                hid_gesture,
                "_hid",
                SimpleNamespace(device=lambda: fake_dev),
                create=True,
            ),
            patch("builtins.print"),
        ):
            self.assertTrue(listener._try_connect())

        self.assertIn("gesture", listener.connected_device.supported_buttons)
        self.assertNotIn("gesture_up", listener.connected_device.supported_buttons)
        self.assertNotIn("mode_shift", listener.connected_device.supported_buttons)

    def test_try_connect_preserves_directional_gestures_after_rawxy_divert(self):
        listener = hid_gesture.HidGestureListener()
        info = {
            "product_id": 0xB034,
            "usage_page": 0xFF00,
            "usage": 0x0001,
            "source": "hidapi-enumerate",
            "product_string": "MX Master 3S",
            "path": b"/dev/hidraw-test",
        }
        controls = [
            {"cid": 0x0052, "flags": 0x0030, "mapping_flags": 0x0001},
            {"cid": 0x0053, "flags": 0x0030, "mapping_flags": 0x0001},
            {"cid": 0x0056, "flags": 0x0030, "mapping_flags": 0x0001},
            {"cid": 0x00C3, "flags": 0x0130, "mapping_flags": 0x0011},
            {"cid": 0x00C4, "flags": 0x0130, "mapping_flags": 0x0001},
        ]
        fake_dev = _FakeHidDevice()

        def fake_find_feature(feature_id):
            if feature_id == hid_gesture.FEAT_REPROG_V4:
                return 0x09
            return None

        def fake_divert():
            listener._gesture_cid = 0x00C3
            listener._rawxy_enabled = True
            return True

        with (
            patch.object(listener, "_vendor_hid_infos", return_value=[info]),
            patch.object(listener, "_find_feature", side_effect=fake_find_feature),
            patch.object(listener, "_discover_reprog_controls", return_value=controls),
            patch.object(listener, "_divert", side_effect=fake_divert),
            patch.object(listener, "_divert_extras"),
            patch.object(hid_gesture, "HIDAPI_OK", True),
            patch.object(hid_gesture, "_BACKEND_PREFERENCE", "hidapi"),
            patch.object(hid_gesture, "_HID_API_STYLE", "hidapi"),
            patch.object(
                hid_gesture,
                "_hid",
                SimpleNamespace(device=lambda: fake_dev),
                create=True,
            ),
            patch("builtins.print"),
        ):
            self.assertTrue(listener._try_connect())

        self.assertIn("gesture", listener.connected_device.supported_buttons)
        self.assertIn("gesture_up", listener.connected_device.supported_buttons)
        self.assertIn("mode_shift", listener.connected_device.supported_buttons)

    def test_transport_label_logi_bolt_for_bolt_receiver(self):
        """devIdx 1-6 with Bolt PID 0xC548 should produce 'Logi Bolt'."""
        listener = hid_gesture.HidGestureListener()
        info = {
            "product_id": 0xC548,
            "usage_page": 0xFF00,
            "usage": 0x0001,
            "source": "hidapi-enumerate",
            "product_string": "USB Receiver",
            "path": b"/dev/hidraw-test",
        }
        fake_dev = _FakeHidDevice()
        call_count = [0]

        def fake_find_feature(feature_id):
            if feature_id != hid_gesture.FEAT_REPROG_V4:
                return None
            call_count[0] += 1
            return 0x09 if call_count[0] >= 2 else None

        with (
            patch.object(listener, "_vendor_hid_infos", return_value=[info]),
            patch.object(listener, "_find_feature", side_effect=fake_find_feature),
            patch.object(listener, "_discover_reprog_controls", return_value=[]),
            patch.object(listener, "_divert", return_value=True),
            patch.object(listener, "_divert_extras"),
            patch.object(hid_gesture, "HIDAPI_OK", True),
            patch.object(hid_gesture, "_BACKEND_PREFERENCE", "hidapi"),
            patch.object(hid_gesture, "_HID_API_STYLE", "hidapi"),
            patch.object(
                hid_gesture,
                "_hid",
                SimpleNamespace(device=lambda: fake_dev),
                create=True,
            ),
            patch("builtins.print"),
        ):
            self.assertTrue(listener._try_connect())

        self.assertEqual(listener.connected_device.transport, "Logi Bolt")

    def test_transport_label_usb_receiver_for_non_bolt(self):
        """devIdx 1-6 with non-Bolt PID (e.g. Unifying 0xC52B) should produce
        'USB Receiver', not 'Logi Bolt'."""
        listener = hid_gesture.HidGestureListener()
        info = {
            "product_id": 0xC52B,
            "usage_page": 0xFF00,
            "usage": 0x0001,
            "source": "hidapi-enumerate",
            "product_string": "USB Receiver",
            "path": b"/dev/hidraw-test",
        }
        fake_dev = _FakeHidDevice()
        call_count = [0]

        def fake_find_feature(feature_id):
            if feature_id != hid_gesture.FEAT_REPROG_V4:
                return None
            call_count[0] += 1
            return 0x09 if call_count[0] >= 2 else None

        with (
            patch.object(listener, "_vendor_hid_infos", return_value=[info]),
            patch.object(listener, "_find_feature", side_effect=fake_find_feature),
            patch.object(listener, "_discover_reprog_controls", return_value=[]),
            patch.object(listener, "_divert", return_value=True),
            patch.object(listener, "_divert_extras"),
            patch.object(hid_gesture, "HIDAPI_OK", True),
            patch.object(hid_gesture, "_BACKEND_PREFERENCE", "hidapi"),
            patch.object(hid_gesture, "_HID_API_STYLE", "hidapi"),
            patch.object(
                hid_gesture,
                "_hid",
                SimpleNamespace(device=lambda: fake_dev),
                create=True,
            ),
            patch("builtins.print"),
        ):
            self.assertTrue(listener._try_connect())

        self.assertEqual(listener.connected_device.transport, "USB Receiver")


class HidReconnectInvariantTests(unittest.TestCase):
    def test_force_release_stale_holds_clears_gesture_and_extra_buttons(self):
        gesture_up = Mock()
        extra_up = Mock()
        listener = hid_gesture.HidGestureListener(
            on_up=gesture_up,
            extra_diverts={0x00C4: {"on_up": extra_up}},
        )
        listener._held = True
        listener._extra_diverts[0x00C4]["held"] = True

        listener._force_release_stale_holds()

        self.assertFalse(listener._held)
        self.assertFalse(listener._extra_diverts[0x00C4]["held"])
        gesture_up.assert_called_once_with()
        extra_up.assert_called_once_with()


class MXMechanicalMiniMiddlePathTests(unittest.TestCase):
    """Focused tests for the MX Mechanical Mini keyboard middle-path features
    (BACKLIGHT2 + K375S_FN_INVERSION). These complement the broader Phase 0
    classification and multi-receiver hygiene work.

    Manual validation checklist (run with real hardware when possible):
    1. Plug both receivers (Lightspeed c547 + Bolt c548).
    2. Launch Mouser — G502 X should still appear quickly as "mouse".
    3. MX Mechanical Mini should be detected as "keyboard" (check debug logs or device info).
    4. Call read_backlight() / set_backlight() via the backend (or future UI) — changes must be marked temporary.
    5. Reconnect or switch hosts — host-side backlight/FN changes should be lost (onboard state wins).
    6. Confirm no mouse gesture paths or RawXY attempts are made on the keyboard device.
    """

    def setUp(self):
        self.listener = hid_gesture.HidGestureListener()

    # ------------------------------------------------------------------
    # Classification tests (expanded per reviewer feedback)
    # ------------------------------------------------------------------
    def test_classify_device_kind_detects_keyboard_via_backlight2(self):
        """BACKLIGHT2 presence (without mouse DPI/ONBOARD) should classify as keyboard."""
        kind = hid_gesture.classify_device_kind(
            pid=0xB367,
            product_name="MX Mechanical Mini",
            discovered_feature_ids={0x1982},  # BACKLIGHT2
        )
        self.assertEqual(kind, "keyboard")

    def test_classify_device_kind_prefers_mouse_when_dpi_present(self):
        """Even if BACKLIGHT2 is somehow reported, DPI/ONBOARD should win as mouse."""
        kind = hid_gesture.classify_device_kind(
            pid=0xB367,
            product_name="MX Mechanical Mini",
            discovered_feature_ids={0x1982, 0x2201},  # BACKLIGHT2 + DPI
        )
        self.assertEqual(kind, "mouse")

    def test_classify_device_kind_name_based_keyboard(self):
        """Name-based heuristics should catch the MX Mechanical Mini."""
        kind = hid_gesture.classify_device_kind(
            pid=0x0000,
            product_name="MX Mechanical Mini",
        )
        self.assertEqual(kind, "keyboard")

    def test_classify_device_kind_feature_only_neutral_name(self):
        """Feature-only classification should still work with an empty product name."""
        kind = hid_gesture.classify_device_kind(
            pid=0x0000,
            product_name="",
            discovered_feature_ids={0x1982},
        )
        self.assertEqual(kind, "keyboard")

    # ------------------------------------------------------------------
    # Apply + pending state machine tests (highest leverage per reviewer)
    # ------------------------------------------------------------------
    def test_apply_pending_read_backlight_success_and_failure(self):
        """Directly test the apply helper + result/pending state (the real implementation surface)."""
        self.listener._backlight2_idx = 0x0A
        self.listener._dev = Mock()

        with patch.object(self.listener, "_request") as m:
            # Success path
            m.return_value = (None, None, None, None, b"\x01\x00\x00\x50\x00")
            self.listener._apply_pending_read_backlight()
            self.assertEqual(self.listener._backlight_result, (True, 0x50))
            self.assertIsNone(self.listener._pending_backlight)

            # Failure path
            m.return_value = None
            self.listener._apply_pending_read_backlight()
            self.assertEqual(self.listener._backlight_result, (None, None))
            self.assertIsNone(self.listener._pending_backlight)

    def test_read_backlight_timeout_clears_pending(self):
        """Public read method must clear pending on timeout (matches DPI pattern)."""
        self.listener._backlight2_idx = 0x0A
        # Force the timeout path by making the loop run without the apply clearing pending
        with patch("time.sleep"):
            res = self.listener.read_backlight()

        self.assertIsNone(self.listener._pending_backlight)
        self.assertEqual(res, (None, None))

    # ------------------------------------------------------------------
    # FN inversion coverage (was completely missing)
    # ------------------------------------------------------------------
    def test_read_write_fn_inversion_basic_paths(self):
        """Basic smoke test for the FN inversion methods (apply + timeout behavior)."""
        self.listener._fn_inversion_idx = 0x0B
        self.listener._dev = Mock()

        with patch.object(self.listener, "_request") as m:
            m.return_value = (None, None, None, None, b"\x01")
            self.listener._apply_pending_read_fn_inversion()
            self.assertTrue(self.listener._fn_result)

    def test_public_methods_early_return_when_index_none(self):
        """All public methods must early-return cleanly when the feature index is not present."""
        self.assertEqual(self.listener.read_backlight(), (None, None))
        self.assertFalse(self.listener.set_backlight(True))
        self.assertIsNone(self.listener.read_fn_inversion())
        self.assertFalse(self.listener.set_fn_inversion(True))

    def test_discover_common_features_populates_keyboard_indexes(self):
        """_discover_common_features should set the backlight2 and fn_inversion indexes when present."""
        listener = hid_gesture.HidGestureListener()
        listener._dev = Mock()

        with patch.object(listener, "_find_feature") as m:
            m.side_effect = lambda fid: 0x0A if fid in (0x1982, 0x40A3) else None
            listener._discover_common_features()

        self.assertEqual(listener._backlight2_idx, 0x0A)
        self.assertEqual(listener._fn_inversion_idx, 0x0A)

    def test_apply_pending_set_backlight_and_timeout(self):
        """Test set apply success and timeout pending-clear behavior."""
        self.listener._backlight2_idx = 0x0A
        self.listener._dev = Mock()

        with patch.object(self.listener, "_request") as m:
            m.return_value = (None, None, None, None, b"")  # success (any non-None)
            self.listener._pending_backlight = ("set", True, 50)
            self.listener._apply_pending_set_backlight(True, 50)
            self.assertTrue(self.listener._backlight_result)
            self.assertIsNone(self.listener._pending_backlight)

        # Timeout case (no apply clears it)
        self.listener._pending_backlight = ("set", True, 50)
        with patch("time.sleep"):
            res = self.listener.set_backlight(True, 50)
        self.assertIsNone(self.listener._pending_backlight)
        self.assertFalse(res)

    def test_apply_pending_set_fn_inversion(self):
        """Basic coverage for FN set apply."""
        self.listener._fn_inversion_idx = 0x0B
        self.listener._dev = Mock()

        with patch.object(self.listener, "_request") as m:
            m.return_value = (None, None, None, None, b"")
            self.listener._pending_fn = ("set", False)
            self.listener._apply_pending_set_fn_inversion(False)
            self.assertTrue(self.listener._fn_result)
            self.assertIsNone(self.listener._pending_fn)

    def test_candidate_sort_prefers_mouse_before_keyboard(self):
        """Multi-receiver setups should try mouse candidates before keyboard."""
        listener = hid_gesture.HidGestureListener()
        infos = [
            {
                "product_id": 0xB367,
                "product_string": "MX Mechanical Mini",
                "usage_page": 0xFF00,
                "usage": 0x0001,
                "source": "hidapi",
            },
            {
                "product_id": 0xC099,
                "product_string": "G502 X LIGHTSPEED",
                "usage_page": 0xFF00,
                "usage": 0x0001,
                "source": "hidapi",
            },
        ]

        def _sort_key(info):
            pid = int(info.get("product_id", 0) or 0)
            name = (info.get("product_string") or "").lower()
            kind = hid_gesture.classify_device_kind(pid, name)
            kind_prio = {"mouse": 0, "unknown": 1, "other": 2, "keyboard": 3}.get(kind, 4)
            is_receiver = 1 if "receiver" in name else 0
            return (kind_prio, is_receiver, name)

        infos.sort(key=_sort_key)
        self.assertEqual(infos[0]["product_string"], "G502 X LIGHTSPEED")

    def test_discover_common_features_populates_litra_illumination_index(self):
        """Litra ILLUMINATION uses HID++ 0x1990 (Solaar), not PRESENTER_CONTROL 0x1A00."""
        listener = hid_gesture.HidGestureListener()
        listener._dev = Mock()

        def _find_feature(feature_id):
            if feature_id == hid_gesture.FEAT_LITRA_ILLUMINATION:
                return 0x0D
            return None

        with patch.object(listener, "_find_feature", side_effect=_find_feature):
            listener._discover_common_features()

        self.assertEqual(listener._litra_illumination_idx, 0x0D)

    def test_try_connect_keyboard_short_circuits_reprog_and_divert(self):
        """Keyboard with REPROG must still skip reprog walk + gesture diversion."""
        listener = hid_gesture.HidGestureListener()
        mock_dev = Mock()
        mock_dev.close = Mock()

        candidate = {
            "product_id": 0xB367,
            "usage_page": 0xFF00,
            "usage": 0x0001,
            "transport": "USB",
            "source": "hidapi",
            "product_string": "MX Mechanical Mini",
            "path": b"/dev/hidraw-test",
        }

        fake_hid_device = Mock()
        fake_hid_device.set_nonblocking = Mock()

        def _find_feature_side_effect(feat_id):
            if feat_id == hid_gesture.FEAT_REPROG_V4:
                return 0x0A
            if feat_id == hid_gesture.FEAT_BACKLIGHT2:
                return 0x0B
            if feat_id == hid_gesture.FEAT_K375S_FN_INVERSION:
                return 0x0C
            return None

        with (
            patch.object(listener, "_vendor_hid_infos", return_value=[candidate]),
            patch.object(hid_gesture, "HIDAPI_OK", True),
            patch.object(hid_gesture, "_HID_API_STYLE", "hidapi"),
            patch.object(hid_gesture, "_BACKEND_PREFERENCE", "hidapi"),
            patch.object(hid_gesture._hid, "device", return_value=fake_hid_device),
            patch.object(fake_hid_device, "open_path"),
            patch.object(listener, "_find_feature", side_effect=_find_feature_side_effect),
            patch.object(listener, "_query_device_name", return_value="MX Mechanical Mini"),
            patch.object(listener, "_discover_reprog_controls") as reprog_mock,
            patch.object(listener, "_divert") as divert_mock,
        ):
            result = listener._try_connect()

        self.assertTrue(result)
        reprog_mock.assert_not_called()
        divert_mock.assert_not_called()
        info = listener.connected_device
        self.assertIsNotNone(info)
        identity = dict(info.capability_inventory.device_identity)
        self.assertEqual(identity.get("device_kind"), "keyboard")
        self.assertTrue(info.capability_inventory.keyboard_device)
        self.assertEqual(info.gesture_cids, ())
        self.assertFalse(info.capability_inventory.has_reprog_controls)


class KeyboardHostReplayTests(unittest.TestCase):
    """Engine replays per-device host-side keyboard settings on HID++ reconnect."""

    def _make_engine(self, device_key="B367"):
        import copy
        from core.engine import Engine
        from tests.test_smart_shift import _FakeAppDetector, _FakeMouseHook

        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg.setdefault("devices", {})[device_key] = {
            "keyboard_middle_path": {
                "allow_host_backlight": True,
                "allow_fn_inversion": True,
                "host_backlight_enabled": True,
                "host_backlight_level": 40,
                "host_fn_inversion": True,
            }
        }
        with (
            patch("core.engine.MouseHook", _FakeMouseHook),
            patch("core.engine.AppDetector", _FakeAppDetector),
            patch("core.engine.load_config", return_value=cfg),
            patch("core.engine.save_config"),
        ):
            return Engine()

    def test_replay_saved_keyboard_host_settings(self):
        engine = self._make_engine()
        hg = Mock()
        hg.connected_device = SimpleNamespace(key="B367", product_id=0xB367)
        hg._backlight2_idx = 0x0A
        hg._fn_inversion_idx = 0x0B
        hg.set_backlight.return_value = True
        hg.set_fn_inversion.return_value = True
        engine.hook._hid_gesture = hg

        self.assertTrue(engine._replay_saved_keyboard_host_settings(hg))
        hg.set_backlight.assert_called_once_with(True, 40)
        hg.set_fn_inversion.assert_called_once_with(True)

    def test_replay_skips_when_allow_host_flags_disabled(self):
        import copy
        from core.engine import Engine
        from tests.test_smart_shift import _FakeAppDetector, _FakeMouseHook

        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg.setdefault("devices", {})["B367"] = {
            "keyboard_middle_path": {
                "allow_host_backlight": False,
                "allow_fn_inversion": False,
                "host_backlight_enabled": True,
                "host_backlight_level": 40,
                "host_fn_inversion": True,
            }
        }
        with (
            patch("core.engine.MouseHook", _FakeMouseHook),
            patch("core.engine.AppDetector", _FakeAppDetector),
            patch("core.engine.load_config", return_value=cfg),
            patch("core.engine.save_config"),
        ):
            engine = Engine()

        hg = Mock()
        hg.connected_device = SimpleNamespace(key="B367", product_id=0xB367)
        hg._backlight2_idx = 0x0A
        hg._fn_inversion_idx = 0x0B
        engine.hook._hid_gesture = hg

        self.assertTrue(engine._replay_saved_keyboard_host_settings(hg))
        hg.set_backlight.assert_not_called()
        hg.set_fn_inversion.assert_not_called()


class KeyboardHandlerDelegationTests(unittest.TestCase):
    """Engine delegates keyboard middle-path APIs through FeatureHandlers (004.5)."""

    def _make_engine(self, device_key="B367", kmp_overrides=None):
        import copy
        from core.engine import Engine
        from tests.test_smart_shift import _FakeAppDetector, _FakeMouseHook

        cfg = copy.deepcopy(DEFAULT_CONFIG)
        kmp = {
            "allow_host_backlight": True,
            "allow_fn_inversion": True,
        }
        if kmp_overrides:
            kmp.update(kmp_overrides)
        cfg.setdefault("devices", {})[device_key] = {"keyboard_middle_path": kmp}
        device = SimpleNamespace(key=device_key, product_id=0xB367)
        with (
            patch("core.engine.MouseHook", _FakeMouseHook),
            patch("core.engine.AppDetector", _FakeAppDetector),
            patch("core.engine.load_config", return_value=cfg),
            patch("core.engine.save_config"),
        ):
            engine = Engine()
            engine.hook.connected_device = device
        return engine

    def test_read_backlight_attaches_handler_and_delegates(self):
        engine = self._make_engine()
        hg = Mock()
        hg.connected_device = SimpleNamespace(key="B367", product_id=0xB367)
        hg._backlight2_idx = 0x0A
        hg.read_backlight.return_value = (True, 50)
        engine.hook._hid_gesture = hg

        result = engine.read_backlight()

        self.assertEqual(result, (True, 50))
        self.assertIsNotNone(engine._backlight_device)
        hg.read_backlight.assert_called_once_with()

    def test_set_backlight_blocked_by_per_device_setting(self):
        engine = self._make_engine(kmp_overrides={"allow_host_backlight": False})
        hg = Mock()
        hg.connected_device = SimpleNamespace(key="B367", product_id=0xB367)
        hg._backlight2_idx = 0x0A
        engine.hook._hid_gesture = hg

        with patch("core.engine.save_keyboard_host_backlight_state") as save_bl:
            self.assertFalse(engine.set_backlight(True, 40))
            hg.set_backlight.assert_not_called()
            save_bl.assert_not_called()

    def test_set_backlight_delegates_and_persists_host_state(self):
        engine = self._make_engine()
        hg = Mock()
        hg.connected_device = SimpleNamespace(key="B367", product_id=0xB367)
        hg._backlight2_idx = 0x0A
        hg.set_backlight.return_value = True
        engine.hook._hid_gesture = hg

        with patch("core.engine.save_keyboard_host_backlight_state") as save_bl:
            self.assertTrue(engine.set_backlight(True, 40))
            self.assertIsNotNone(engine._backlight_device)
            hg.set_backlight.assert_called_once_with(True, 40)
            save_bl.assert_called_once_with(engine.cfg, "B367", True, 40)

    def test_read_fn_inversion_attaches_handler_and_delegates(self):
        engine = self._make_engine()
        hg = Mock()
        hg.connected_device = SimpleNamespace(key="B367", product_id=0xB367)
        hg._fn_inversion_idx = 0x0B
        hg.read_fn_inversion.return_value = True
        engine.hook._hid_gesture = hg

        self.assertTrue(engine.read_fn_inversion())
        self.assertIsNotNone(engine._fn_inversion_device)
        hg.read_fn_inversion.assert_called_once_with()

    def test_set_fn_inversion_blocked_by_per_device_setting(self):
        engine = self._make_engine(kmp_overrides={"allow_fn_inversion": False})
        hg = Mock()
        hg.connected_device = SimpleNamespace(key="B367", product_id=0xB367)
        hg._fn_inversion_idx = 0x0B
        engine.hook._hid_gesture = hg

        with patch("core.engine.save_keyboard_host_fn_inversion_state") as save_fn:
            self.assertFalse(engine.set_fn_inversion(True))
            hg.set_fn_inversion.assert_not_called()
            save_fn.assert_not_called()

    def test_set_fn_inversion_delegates_and_persists_host_state(self):
        engine = self._make_engine()
        hg = Mock()
        hg.connected_device = SimpleNamespace(key="B367", product_id=0xB367)
        hg._fn_inversion_idx = 0x0B
        hg.set_fn_inversion.return_value = True
        engine.hook._hid_gesture = hg

        with patch("core.engine.save_keyboard_host_fn_inversion_state") as save_fn:
            self.assertTrue(engine.set_fn_inversion(False))
            self.assertIsNotNone(engine._fn_inversion_device)
            hg.set_fn_inversion.assert_called_once_with(False)
            save_fn.assert_called_once_with(engine.cfg, "B367", False)


if __name__ == "__main__":
    unittest.main()
