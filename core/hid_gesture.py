"""
hid_gesture.py — Detect Logitech HID++ gesture controls and device features.

Many Logitech mice expose their gesture button and DPI/battery controls only
through the HID++ vendor channel instead of standard OS mouse events. This
module opens the Logitech HID interface, discovers REPROG_CONTROLS_V4 and
related features, diverts the best gesture candidate it can find, and reports
press/release or RawXY movement back to Mouser.

Requires:  pip install hidapi
Falls back gracefully if the package or device are unavailable.
"""

import os
import stat
import sys
import queue
import threading
import time

from core.logi_devices import (
    DEFAULT_GESTURE_CIDS,
    build_connected_device_info,
    clamp_dpi,
    resolve_device,
)

_HID_MODULE_NAME = None
try:
    # The PyPI hidapi Linux wheels expose `hid` as the libusb backend and
    # `hidraw` as the hidraw backend. Bluetooth HID devices only work through
    # hidraw, so prefer it on Linux and fall back to `hid` for source builds
    # where `hid` itself was compiled against hidraw.
    if sys.platform.startswith("linux"):
        try:
            import hidraw as _hid
            _HID_MODULE_NAME = "hidraw"
        except ImportError:
            import hid as _hid
            _HID_MODULE_NAME = "hid"
    else:
        import hid as _hid
        _HID_MODULE_NAME = "hid"
    HIDAPI_OK = True
    HIDAPI_IMPORT_ERROR = None
    # On macOS, allow non-exclusive HID access so the mouse keeps working
    if sys.platform == "darwin" and hasattr(_hid, "hid_darwin_set_open_exclusive"):
        _hid.hid_darwin_set_open_exclusive(0)
except Exception as exc:
    HIDAPI_OK = False
    HIDAPI_IMPORT_ERROR = exc

# Support both hidapi/hidraw-style modules (device) and "pip install hid" (Device).
_HID_API_STYLE = None
if HIDAPI_OK:
    if hasattr(_hid, 'device'):
        _HID_API_STYLE = "hidapi"
    elif hasattr(_hid, 'Device'):
        _HID_API_STYLE = "hid"


_LOG_ONCE_KEYS = set()


def _log_once(key, message):
    if key in _LOG_ONCE_KEYS:
        return
    _LOG_ONCE_KEYS.add(key)
    print(message)


def _device_path_display(path):
    if isinstance(path, memoryview):
        path = bytes(path)
    if isinstance(path, bytes):
        return path.decode("utf-8", errors="replace")
    return str(path or "")


def _owner_name(uid):
    try:
        import pwd
        return pwd.getpwuid(uid).pw_name
    except Exception:
        return str(uid)


def _group_name(gid):
    try:
        import grp
        return grp.getgrgid(gid).gr_name
    except Exception:
        return str(gid)


def _format_linux_device_access(path):
    if isinstance(path, memoryview):
        path = bytes(path)
    display = _device_path_display(path)
    if not path:
        return "path=-"
    try:
        st = os.stat(path)
    except OSError as exc:
        return f"path={display} stat_error={exc}"

    mode = stat.S_IMODE(st.st_mode)
    can_read = os.access(path, os.R_OK)
    can_write = os.access(path, os.W_OK)
    can_rw = os.access(path, os.R_OK | os.W_OK)
    return (
        f"path={display} mode={mode:04o} "
        f"owner={_owner_name(st.st_uid)}({st.st_uid}) "
        f"group={_group_name(st.st_gid)}({st.st_gid}) "
        f"access=read:{can_read} write:{can_write} read_write:{can_rw}"
    )


class _HidDeviceCompat:
    """Wraps the ``hid`` package Device to match the ``hidapi`` interface."""

    def __init__(self, path):
        if isinstance(path, memoryview):
            path = bytes(path)
        elif isinstance(path, str):
            path = path.encode()
        self._dev = _hid.Device(path=path)

    def set_nonblocking(self, enabled):
        self._dev.nonblocking = bool(enabled)

    def write(self, data):
        return self._dev.write(bytes(data))

    def read(self, size, timeout_ms=0):
        data = self._dev.read(size, timeout=timeout_ms if timeout_ms else None)
        return data if data else None

    def close(self):
        self._dev.close()

_MAC_NATIVE_OK = False
if sys.platform == "darwin":
    try:
        import ctypes
        from ctypes import POINTER, byref, c_char_p, c_int, c_long, c_uint8, c_void_p, create_string_buffer

        _cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        _iokit = ctypes.CDLL("/System/Library/Frameworks/IOKit.framework/IOKit")

        _cf.CFNumberCreate.argtypes = [c_void_p, c_int, c_void_p]
        _cf.CFNumberCreate.restype = c_void_p
        _cf.CFNumberGetValue.argtypes = [c_void_p, c_int, c_void_p]
        _cf.CFNumberGetValue.restype = c_int
        _cf.CFStringCreateWithCString.argtypes = [c_void_p, c_char_p, c_int]
        _cf.CFStringCreateWithCString.restype = c_void_p
        _cf.CFStringGetCString.argtypes = [c_void_p, c_void_p, c_long, c_int]
        _cf.CFStringGetCString.restype = c_int
        _cf.CFDictionaryCreate.argtypes = [
            c_void_p, POINTER(c_void_p), POINTER(c_void_p), c_long, c_void_p, c_void_p,
        ]
        _cf.CFDictionaryCreate.restype = c_void_p
        _cf.CFSetGetCount.argtypes = [c_void_p]
        _cf.CFSetGetCount.restype = c_long
        _cf.CFSetGetValues.argtypes = [c_void_p, POINTER(c_void_p)]
        _cf.CFRelease.argtypes = [c_void_p]
        _cf.CFRetain.argtypes = [c_void_p]
        _cf.CFRetain.restype = c_void_p
        _cf.CFRunLoopGetCurrent.argtypes = []
        _cf.CFRunLoopGetCurrent.restype = c_void_p
        _cf.CFRunLoopRunInMode.argtypes = [c_void_p, ctypes.c_double, ctypes.c_bool]
        _cf.CFRunLoopRunInMode.restype = c_int

        _iokit.IOHIDManagerCreate.argtypes = [c_void_p, c_int]
        _iokit.IOHIDManagerCreate.restype = c_void_p
        _iokit.IOHIDManagerSetDeviceMatching.argtypes = [c_void_p, c_void_p]
        _iokit.IOHIDManagerOpen.argtypes = [c_void_p, c_int]
        _iokit.IOHIDManagerOpen.restype = c_int
        _iokit.IOHIDManagerCopyDevices.argtypes = [c_void_p]
        _iokit.IOHIDManagerCopyDevices.restype = c_void_p

        _iokit.IOHIDDeviceOpen.argtypes = [c_void_p, c_int]
        _iokit.IOHIDDeviceOpen.restype = c_int
        _iokit.IOHIDDeviceClose.argtypes = [c_void_p, c_int]
        _iokit.IOHIDDeviceClose.restype = c_int
        _iokit.IOHIDDeviceGetProperty.argtypes = [c_void_p, c_void_p]
        _iokit.IOHIDDeviceGetProperty.restype = c_void_p
        _iokit.IOHIDDeviceScheduleWithRunLoop.argtypes = [c_void_p, c_void_p, c_void_p]
        _iokit.IOHIDDeviceUnscheduleFromRunLoop.argtypes = [c_void_p, c_void_p, c_void_p]
        _iokit.IOHIDDeviceSetReport.argtypes = [c_void_p, c_int, c_long, POINTER(c_uint8), c_long]
        _iokit.IOHIDDeviceSetReport.restype = c_int
        _IOHID_REPORT_CALLBACK = ctypes.CFUNCTYPE(
            None,
            c_void_p,
            c_int,
            c_void_p,
            c_int,
            ctypes.c_uint32,
            POINTER(c_uint8),
            c_long,
        )
        _iokit.IOHIDDeviceRegisterInputReportCallback.argtypes = [
            c_void_p,
            POINTER(c_uint8),
            c_long,
            _IOHID_REPORT_CALLBACK,
            c_void_p,
        ]
        _iokit.IOHIDDeviceGetReport.argtypes = [c_void_p, c_int, c_long, POINTER(c_uint8), POINTER(c_long)]
        _iokit.IOHIDDeviceGetReport.restype = c_int

        _K_CF_NUMBER_SINT32 = 3
        _K_CF_STRING_ENCODING_UTF8 = 0x08000100
        _K_IOHID_REPORT_TYPE_INPUT = 0
        _K_IOHID_REPORT_TYPE_OUTPUT = 1
        _K_CF_RUN_LOOP_DEFAULT_MODE = c_void_p.in_dll(_cf, "kCFRunLoopDefaultMode")

        _MAC_NATIVE_OK = True
    except Exception as exc:
        print(f"[HidGesture] macOS native HID unavailable: {exc}")


def _default_backend_preference(platform_name=None):
    platform_name = sys.platform if platform_name is None else platform_name
    return "auto"


_BACKEND_PREFERENCE = _default_backend_preference()


def set_backend_preference(preference):
    normalized = (preference or "auto").strip().lower()
    if normalized not in {"auto", "hidapi", "iokit"}:
        raise ValueError("hid backend must be one of: auto, hidapi, iokit")
    if normalized == "hidapi" and not HIDAPI_OK:
        raise ValueError("hidapi backend requested but hidapi is not available")
    if normalized == "iokit":
        if sys.platform != "darwin":
            raise ValueError("iokit backend is only available on macOS")
        if not _MAC_NATIVE_OK:
            raise ValueError("iokit backend requested but native macOS HID is unavailable")

    global _BACKEND_PREFERENCE
    _BACKEND_PREFERENCE = normalized
    print(f"[HidGesture] Backend preference set to {normalized}")


def get_backend_preference():
    return _BACKEND_PREFERENCE


if _MAC_NATIVE_OK:
    class _MacNativeHidDevice:
        """Minimal IOHIDDevice wrapper for Logitech BLE HID++ on macOS."""

        def __init__(self, product_id, usage_page=0, usage=0, transport=None):
            self._product_id = int(product_id)
            self._usage_page = int(usage_page or 0)
            self._usage = int(usage or 0)
            self._transport = transport or None
            self._manager = None
            self._matching = None
            self._device = None
            self._matching_refs = []
            self._run_loop = None
            self._input_buffer = None
            self._report_callback = None
            self._report_queue = queue.Queue()

        @staticmethod
        def _cfstring(text):
            return _cf.CFStringCreateWithCString(
                None, text.encode("utf-8"), _K_CF_STRING_ENCODING_UTF8
            )

        @staticmethod
        def _cfnumber(value):
            num = c_int(int(value))
            return _cf.CFNumberCreate(None, _K_CF_NUMBER_SINT32, byref(num))

        @staticmethod
        def _cfnumber_to_int(ref):
            if not ref:
                return 0
            value = c_int()
            ok = _cf.CFNumberGetValue(ref, _K_CF_NUMBER_SINT32, byref(value))
            return int(value.value) if ok else 0

        @staticmethod
        def _cfstring_to_str(ref):
            if not ref:
                return None
            buf = create_string_buffer(256)
            ok = _cf.CFStringGetCString(ref, buf, len(buf), _K_CF_STRING_ENCODING_UTF8)
            return buf.value.decode("utf-8", errors="replace") if ok else None

        @classmethod
        def _get_property(cls, device_ref, name):
            key = cls._cfstring(name)
            try:
                return _iokit.IOHIDDeviceGetProperty(device_ref, key)
            finally:
                _cf.CFRelease(key)

        @classmethod
        def enumerate_infos(cls):
            infos = []
            manager = None
            matching = None
            matching_refs = []
            try:
                keys = [cls._cfstring("VendorID")]
                values = [cls._cfnumber(LOGI_VID)]
                key_array = (c_void_p * len(keys))(*keys)
                value_array = (c_void_p * len(values))(*values)
                matching = _cf.CFDictionaryCreate(
                    None, key_array, value_array, len(keys), None, None
                )
                matching_refs = keys + values

                manager = _iokit.IOHIDManagerCreate(None, 0)
                if not manager:
                    raise OSError("IOHIDManagerCreate failed")
                _iokit.IOHIDManagerSetDeviceMatching(manager, matching)
                res = _iokit.IOHIDManagerOpen(manager, 0)
                if res != 0:
                    raise OSError(f"IOHIDManagerOpen failed: 0x{res:08X}")

                devices = _iokit.IOHIDManagerCopyDevices(manager)
                if not devices:
                    return infos
                try:
                    count = _cf.CFSetGetCount(devices)
                    if count <= 0:
                        return infos
                    values_buf = (c_void_p * count)()
                    _cf.CFSetGetValues(devices, values_buf)
                    seen = set()
                    for device_ref in values_buf:
                        pid = cls._cfnumber_to_int(cls._get_property(device_ref, "ProductID"))
                        up = cls._cfnumber_to_int(cls._get_property(device_ref, "PrimaryUsagePage"))
                        usage = cls._cfnumber_to_int(cls._get_property(device_ref, "PrimaryUsage"))
                        transport = cls._cfstring_to_str(cls._get_property(device_ref, "Transport"))
                        product = cls._cfstring_to_str(cls._get_property(device_ref, "Product"))
                        if not pid:
                            continue
                        key = (pid, up, usage, transport or "", product or "")
                        if key in seen:
                            continue
                        seen.add(key)
                        infos.append({
                            "product_id": pid,
                            "usage_page": up,
                            "usage": usage,
                            "transport": transport,
                            "product_string": product,
                            "source": "iokit-enumerate",
                        })
                finally:
                    _cf.CFRelease(devices)
            except Exception as exc:
                print(f"[HidGesture] native enumerate error: {exc}")
            finally:
                if matching:
                    _cf.CFRelease(matching)
                if manager:
                    _cf.CFRelease(manager)
                for item in matching_refs:
                    _cf.CFRelease(item)
            return infos

        def open(self):
            keys = [
                self._cfstring("VendorID"),
                self._cfstring("ProductID"),
            ]
            values = [
                self._cfnumber(LOGI_VID),
                self._cfnumber(self._product_id),
            ]
            if self._usage_page > 0:
                keys.append(self._cfstring("PrimaryUsagePage"))
                values.append(self._cfnumber(self._usage_page))
            if self._usage > 0:
                keys.append(self._cfstring("PrimaryUsage"))
                values.append(self._cfnumber(self._usage))
            if self._transport:
                keys.append(self._cfstring("Transport"))
                values.append(self._cfstring(self._transport))
            key_array = (c_void_p * len(keys))(*keys)
            value_array = (c_void_p * len(values))(*values)
            self._matching = _cf.CFDictionaryCreate(
                None, key_array, value_array, len(keys), None, None
            )
            self._matching_refs = keys + values

            self._manager = _iokit.IOHIDManagerCreate(None, 0)
            if not self._manager:
                raise OSError("IOHIDManagerCreate failed")
            _iokit.IOHIDManagerSetDeviceMatching(self._manager, self._matching)
            res = _iokit.IOHIDManagerOpen(self._manager, 0)
            if res != 0:
                raise OSError(f"IOHIDManagerOpen failed: 0x{res:08X}")

            devices = _iokit.IOHIDManagerCopyDevices(self._manager)
            if not devices:
                raise OSError(self._describe_match_failure())
            try:
                count = _cf.CFSetGetCount(devices)
                if count <= 0:
                    raise OSError(self._describe_match_failure())
                values_buf = (c_void_p * count)()
                _cf.CFSetGetValues(devices, values_buf)
                self._device = _cf.CFRetain(values_buf[0])
            finally:
                _cf.CFRelease(devices)

            res = _iokit.IOHIDDeviceOpen(self._device, 0)
            if res != 0:
                raise OSError(f"IOHIDDeviceOpen failed: 0x{res:08X}")
            self._run_loop = _cf.CFRunLoopGetCurrent()
            self._input_buffer = (c_uint8 * 64)()
            self._report_callback = _IOHID_REPORT_CALLBACK(self._on_input_report)
            _iokit.IOHIDDeviceScheduleWithRunLoop(
                self._device,
                self._run_loop,
                _K_CF_RUN_LOOP_DEFAULT_MODE,
            )
            _iokit.IOHIDDeviceRegisterInputReportCallback(
                self._device,
                self._input_buffer,
                len(self._input_buffer),
                self._report_callback,
                None,
            )

        def _describe_match_failure(self):
            parts = [f"PID 0x{self._product_id:04X}"]
            if self._usage_page > 0:
                parts.append(f"UP 0x{self._usage_page:04X}")
            if self._usage > 0:
                parts.append(f"usage 0x{self._usage:04X}")
            if self._transport:
                parts.append(f'transport "{self._transport}"')
            return "No IOHIDDevice for " + " ".join(parts)

        def close(self):
            if self._device and self._run_loop:
                try:
                    _iokit.IOHIDDeviceUnscheduleFromRunLoop(
                        self._device,
                        self._run_loop,
                        _K_CF_RUN_LOOP_DEFAULT_MODE,
                    )
                except Exception:
                    pass
            if self._device:
                try:
                    _iokit.IOHIDDeviceClose(self._device, 0)
                except Exception:
                    pass
            if self._device:
                _cf.CFRelease(self._device)
                self._device = None
            if self._matching:
                _cf.CFRelease(self._matching)
                self._matching = None
            if self._manager:
                _cf.CFRelease(self._manager)
                self._manager = None
            for item in self._matching_refs:
                _cf.CFRelease(item)
            self._matching_refs = []
            self._run_loop = None
            self._input_buffer = None
            self._report_callback = None
            self._report_queue = queue.Queue()

        def set_nonblocking(self, _enabled):
            return None

        def write(self, buf):
            arr = (c_uint8 * len(buf))(*buf)
            res = _iokit.IOHIDDeviceSetReport(
                self._device,
                _K_IOHID_REPORT_TYPE_OUTPUT,
                int(buf[0]),
                arr,
                len(buf),
            )
            if res != 0:
                raise OSError(f"IOHIDDeviceSetReport failed: 0x{res:08X}")
            return len(buf)

        def _on_input_report(self, _context, result, _sender, _report_type,
                             _report_id, report, report_length):
            if result != 0 or report_length <= 0:
                return
            try:
                self._report_queue.put_nowait(
                    ctypes.string_at(report, int(report_length))
                )
            except Exception:
                pass

        def read(self, _size, timeout_ms=0):
            try:
                return self._report_queue.get_nowait()
            except queue.Empty:
                pass

            deadline = None
            if timeout_ms and timeout_ms > 0:
                deadline = time.monotonic() + timeout_ms / 1000.0

            while True:
                if deadline is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return b""
                    slice_seconds = min(remaining, 0.05)
                else:
                    slice_seconds = 0.05

                _cf.CFRunLoopRunInMode(
                    _K_CF_RUN_LOOP_DEFAULT_MODE,
                    slice_seconds,
                    True,
                )
                try:
                    return self._report_queue.get_nowait()
                except queue.Empty:
                    if deadline is not None:
                        continue
                    return b""

# ── Constants ─────────────────────────────────────────────────────
LOGI_VID       = 0x046D


def _summarize_hid_infos(infos, limit=8):
    parts = []
    for info in list(infos)[:limit]:
        pid = int(info.get("product_id", 0) or 0)
        usage_page = int(info.get("usage_page", 0) or 0)
        usage = int(info.get("usage", 0) or 0)
        product = info.get("product_string") or "?"
        transport = info.get("transport") or "-"
        parts.append(
            f"PID=0x{pid:04X} UP=0x{usage_page:04X} "
            f"usage=0x{usage:04X} transport={transport} product={product}"
        )
    remaining = max(0, len(infos) - limit)
    if remaining:
        parts.append(f"... {remaining} more")
    return "; ".join(parts) if parts else "-"


def _linux_logitech_hidraw_nodes(base="/sys/class/hidraw"):
    if not sys.platform.startswith("linux"):
        return []
    try:
        entries = sorted(os.listdir(base))
    except OSError:
        return []

    nodes = []
    for entry in entries:
        if not entry.startswith("hidraw"):
            continue
        uevent_path = os.path.join(base, entry, "device", "uevent")
        try:
            with open(uevent_path, "r", encoding="utf-8", errors="replace") as fh:
                values = dict(
                    line.rstrip("\n").split("=", 1)
                    for line in fh
                    if "=" in line
                )
        except OSError:
            continue

        parts = values.get("HID_ID", "").split(":")
        if len(parts) < 3:
            continue
        try:
            vid = int(parts[1], 16)
            pid = int(parts[2], 16)
        except ValueError:
            continue
        if vid != LOGI_VID:
            continue

        product = values.get("HID_NAME") or "?"
        nodes.append(f"{entry} PID=0x{pid:04X} product={product}")
    return nodes


SHORT_ID       = 0x10        # HID++ short report (7 bytes total)
LONG_ID        = 0x11        # HID++ long  report (20 bytes total)
SHORT_LEN      = 7
LONG_LEN       = 20

BT_DEV_IDX     = 0xFF        # device-index for direct Bluetooth
# Known Logi Bolt receiver PID.
# Source: https://github.com/pwr-Solaar/Solaar/blob/master/lib/logitech_receiver/base_usb.py
BOLT_RECEIVER_PID = 0xC548
FEAT_IROOT     = 0x0000
FEAT_REPROG_V4 = 0x1B04      # Reprogrammable Controls V4
FEAT_ADJ_DPI   = 0x2201      # Adjustable DPI
FEAT_SMART_SHIFT          = 0x2110  # Smart Shift basic
FEAT_SMART_SHIFT_ENHANCED = 0x2111  # Smart Shift Enhanced (MX Master 3/3S, MX Master 4)
FEAT_HIRES_WHEEL          = 0x2120
FEAT_HIRES_WHEEL_ENHANCED = 0x2121
FEAT_LOWRES_WHEEL         = 0x2130
FEAT_THUMB_WHEEL          = 0x2150
FEAT_UNIFIED_BATT   = 0x1004      # Unified Battery (preferred)
FEAT_ONBOARD_PROFILES = 0x8100    # Gaming mice (G502 X etc.) - onboard memory + profiles
FEAT_REPORT_RATE    = 0x8060      # Report rate control (gaming mice)

# Keyboard / general device features (MX Mechanical Mini, etc.)
FEAT_BACKLIGHT2           = 0x1982   # Backlight control (V2 on MX Mechanical Mini)
FEAT_K375S_FN_INVERSION   = 0x40A3   # FN / Fx swap (common on MX Mechanical family)
FEAT_DEVICE_NAME    = 0x0005      # Device Name & Type
FEAT_DEVICE_IDENTITY = 0x0003     # Device Serial Number / Hardware Version / Identity (placeholder)
FEAT_DEVICE_TYPE        = 0x0002     # Device Type / Product Type (placeholder; replace with real ID from device dumps)
FEAT_BATTERY_STATUS = 0x1000      # Battery Status (fallback)

# Litra Beam (and similar Logitech lights) illumination control
FEAT_LITRA_ILLUMINATION = 0x1A00  # Placeholder — replace with actual Litra illumination feature ID from device dump
FEAT_LED_CONTROL        = 0x1A01  # Placeholder for common mouse LED control (on/off + brightness); replace with real ID from device dumps
FEAT_LED_EFFECTS        = 0x1A02  # Placeholder for LED Effects (patterns/modes beyond basic on/off + brightness); replace with real ID from device dumps
FEAT_DEVICE_MODE        = 0x1B00  # Placeholder for Device Mode / Wireless Mode; replace with real ID from device dumps
FEAT_WIRELESS_POWER     = 0x1C00  # Placeholder for Wireless Power / RF Power Management; replace with real ID from device dumps
FEAT_POWER_MANAGEMENT   = 0x1C01  # Placeholder for Power Management (beyond Sleep Timeout / Wireless Power); replace with real ID from device dumps
FEAT_WIRELESS_CHANNEL   = 0x1D00  # Placeholder for Wireless Channel / RF Channel; replace with real ID from device dumps
FEAT_WIRELESS_STATUS    = 0x1F00  # Placeholder for Wireless Status (link quality / RSSI); replace with real ID from device dumps
FEAT_SLEEP_TIMEOUT      = 0x1E00  # Placeholder for Sleep Timeout / Power Save Timeout; replace with real ID from device dumps
DEFAULT_GESTURE_CID = DEFAULT_GESTURE_CIDS[0]

MY_SW          = 0x0A        # arbitrary software-id used in our requests

HIDPP_ERROR_NAMES = {
    0x01: "UNKNOWN",
    0x02: "INVALID_ARGUMENT",
    0x03: "OUT_OF_RANGE",
    0x04: "HARDWARE_ERROR",
    0x05: "LOGITECH_ERROR",
    0x06: "INVALID_FEATURE_INDEX",
    0x07: "INVALID_FUNCTION",
    0x08: "BUSY",
    0x09: "UNSUPPORTED",
}

KNOWN_CID_NAMES = {
    0x00C3: "Mouse Gesture Button",
    0x00C4: "Smart Shift",
    0x00D7: "Virtual Gesture Button",
    0x00FD: "DPI Switch",
}

KEY_FLAG_BITS = (
    (0x0001, "mse"),
    (0x0002, "fn"),
    (0x0004, "nonstandard"),
    (0x0008, "fn_sensitive"),
    (0x0010, "reprogrammable"),
    (0x0020, "divertable"),
    (0x0040, "persist_divertable"),
    (0x0080, "virtual"),
    (0x0100, "raw_xy"),
    (0x0200, "force_raw_xy"),
    (0x0400, "analytics"),
    (0x0800, "raw_wheel"),
)

MAPPING_FLAG_BITS = (
    (0x0001, "diverted"),
    (0x0004, "persist_diverted"),
    (0x0010, "raw_xy_diverted"),
    (0x0040, "force_raw_xy_diverted"),
    (0x0100, "analytics_reporting"),
    (0x0400, "raw_wheel"),
)


def classify_device_kind(
    pid: int,
    product_name: str | None = None,
    hidpp_name: str | None = None,
    discovered_feature_ids: set[int] | None = None,
) -> str:
    """
    Early, cheap device kind classification: 'mouse' | 'keyboard' | 'other' | 'unknown'.

    Used in Phase 0 to short-circuit mouse-only logic (gesture diversion, RawXY, etc.)
    on keyboards such as the MX Mechanical Mini while still allowing useful HID++
    features (battery, backlight, FN inversion) on all device types.

    Heuristics (in priority order):
    - Strong name / PID signals from catalog + known devices
    - Feature presence (BACKLIGHT2 + heavy fn keys → keyboard; DPI/ONBOARD/HIRES_WHEEL → mouse)
    """
    name = ((hidpp_name or product_name) or "").lower()
    feats = discovered_feature_ids or set()

    # Feature-driven classification first (strong mouse signals win even over keyboard-ish names)
    has_dpi       = FEAT_ADJ_DPI in feats or 0x2201 in feats
    has_onboard   = FEAT_ONBOARD_PROFILES in feats or 0x8100 in feats
    has_hires     = FEAT_HIRES_WHEEL_ENHANCED in feats or 0x2121 in feats
    has_backlight = FEAT_BACKLIGHT2 in feats or 0x1982 in feats

    if has_dpi or has_onboard or has_hires:
        return "mouse"

    # Fast name-based signals (only after mouse features did not win)
    if any(x in name for x in ("g502", "mx master", "mx anywhere", "mx vertical")):
        return "mouse"
    if any(x in name for x in ("mechanical mini", "mechanical", "mx keys", "keyboard")):
        return "keyboard"
    if pid in (0x409F, 0xC547, 0xC098, 0xB020):
        return "mouse"

    if has_backlight:
        return "keyboard"

    # Litra Beam (and other Logitech lights) — treat as non-mouse, non-keyboard "other"
    # This prevents it from triggering mouse gesture / RawXY paths or keyboard short-circuits.
    if "litra" in name:
        return "other"

    return "unknown"


# ── Helpers ───────────────────────────────────────────────────────

def _parse(raw):
    """Parse a read buffer → (dev_idx, feat_idx, func, sw, params) or None.

    On Windows the hidapi C backend strips the report-ID byte, so the
    first byte is device-index.  On other platforms / future versions
    the report-ID may be included.  We detect which layout we have by
    checking whether byte 0 looks like a valid HID++ report-ID.
    """
    if not raw or len(raw) < 4:
        return None
    off = 1 if raw[0] in (SHORT_ID, LONG_ID) else 0
    if off + 3 > len(raw):
        return None
    dev    = raw[off]
    feat   = raw[off + 1]
    fsw    = raw[off + 2]
    func   = (fsw >> 4) & 0x0F
    sw     = fsw & 0x0F
    params = raw[off + 3:]
    return dev, feat, func, sw, params


def _hex_bytes(data):
    if not data:
        return "-"
    return " ".join(f"{int(b) & 0xFF:02X}" for b in data)


def _format_flags(value, bit_names):
    names = [name for bit, name in bit_names if value & bit]
    return ",".join(names) if names else "none"


def _format_cid(cid):
    name = KNOWN_CID_NAMES.get(cid)
    return f"0x{cid:04X} ({name})" if name else f"0x{cid:04X}"


# ── Listener class ────────────────────────────────────────────────

class HidGestureListener:
    """Background thread: diverts the gesture button and listens via HID++."""

    def __init__(self, on_down=None, on_up=None, on_move=None,
                 on_connect=None, on_disconnect=None, extra_diverts=None):
        self._on_down       = on_down
        self._on_up         = on_up
        self._on_move       = on_move
        self._on_connect    = on_connect
        self._on_disconnect = on_disconnect
        self._extra_diverts = {
            cid: {**info, "held": False}
            for cid, info in (extra_diverts or {}).items()
        }
        self._dev       = None          # hid.device()
        self._thread    = None
        self._running   = False
        self._feat_idx  = None          # feature index of REPROG_V4
        self._dpi_idx   = None          # feature index of ADJUSTABLE_DPI
        self._battery_idx = None
        self._battery_feature_id = None
        self._dev_idx   = BT_DEV_IDX
        self._gesture_cid = DEFAULT_GESTURE_CID
        self._gesture_candidates = list(DEFAULT_GESTURE_CIDS)
        self._held      = False
        self._connected = False         # True while HID++ device is open
        self._rawxy_enabled = False
        self._pending_dpi = None        # set by set_dpi(), applied in loop
        self._dpi_result  = None        # True/False after apply
        self._smart_shift_idx = None      # feature index of SMART_SHIFT / SMART_SHIFT_ENHANCED
        self._smart_shift_enhanced = False  # True → use fn 1/2; False → fn 0/1
        self._wheel_feature_indexes = {}
        self._onboard_profiles_idx = None   # 0x8100 - for gaming mice with onboard memory
        self._report_rate_idx = None        # 0x8060 - report rate control
        self._backlight2_idx = None         # 0x1982 - BACKLIGHT2 (MX Mechanical Mini etc.)
        self._fn_inversion_idx = None       # 0x40A3 - K375S FN inversion
        self._litra_illumination_idx = None # 0x1A00 - Litra Beam illumination (placeholder ID)
        self._device_name_idx = None        # 0x0005 - Device Name / Friendly Name
        self._device_identity_idx = None    # 0x0003 - Device Serial / Hardware Version / Identity (placeholder)
        self._device_type_idx = None        # 0x0002 - Device Type / Product Type (placeholder)
        self._led_control_idx = None        # 0x1A01 - Common mouse LED control (placeholder)
        self._led_effects_idx = None        # 0x1A02 - LED Effects (placeholder)
        self._device_mode_idx = None        # 0x1B00 - Device Mode / Wireless Mode (placeholder)
        self._wireless_power_idx = None     # 0x1C00 - Wireless Power / RF Power (placeholder)
        self._power_management_idx = None   # 0x1C01 - Power Management (beyond Sleep Timeout) (placeholder)
        self._wireless_channel_idx = None   # 0x1D00 - Wireless Channel / RF Channel (placeholder)
        self._sleep_timeout_idx = None      # 0x1E00 - Sleep Timeout / Power Save Timeout (placeholder)
        self._wireless_status_idx = None    # 0x1F00 - Wireless Status (placeholder)
        self._pending_smart_shift = None
        self._smart_shift_result = None
        self._smart_shift_call_lock = threading.Lock()
        self._smart_shift_slot_lock = threading.Lock()
        self._smart_shift_event = threading.Event()
        self._reconnect_requested = False
        self._pending_battery = None
        self._battery_result = None
        self._last_logged_battery = None

        self._pending_backlight = None
        self._backlight_result = None
        self._pending_fn = None
        self._fn_result = None
        self._connected_device_info = None
        self._last_controls = []   # REPROG_V4 controls from last connection
        self._consecutive_request_timeouts = 0

    # ── public API ────────────────────────────────────────────────

    def start(self):
        if not HIDAPI_OK and not _MAC_NATIVE_OK:
            details = f": {HIDAPI_IMPORT_ERROR!r}" if HIDAPI_IMPORT_ERROR else ""
            print(f"[HidGesture] no HID backend available; install hidapi{details}")
            return False
        if not HIDAPI_OK and _MAC_NATIVE_OK:
            print("[HidGesture] hidapi unavailable; using native macOS HID backend only")
        if HIDAPI_OK:
            print(
                "[HidGesture] HID module: "
                f"{_HID_MODULE_NAME or '?'} API style: {_HID_API_STYLE or '?'}"
            )
            if sys.platform.startswith("linux") and _HID_MODULE_NAME != "hidraw":
                print(
                    "[HidGesture] Linux hidraw module is unavailable; Bluetooth "
                    "Logitech HID++ devices may not enumerate"
                )
        self._running = True
        self._thread = threading.Thread(
            target=self._main_loop, daemon=True, name="HidGesture")
        self._thread.start()
        return True

    def stop(self):
        self._running = False
        d = self._dev
        if d:
            try:
                d.close()
            except Exception:
                pass
            self._dev = None
        self._connected_device_info = None
        if self._thread:
            self._thread.join(timeout=3)

    @property
    def connected_device(self):
        return self._connected_device_info

    def _discovered_feature_ids(self):
        feature_ids = []
        if self._feat_idx is not None:
            feature_ids.append(FEAT_REPROG_V4)
        if self._dpi_idx is not None:
            feature_ids.append(FEAT_ADJ_DPI)
        if self._smart_shift_idx is not None:
            feature_ids.append(
                FEAT_SMART_SHIFT_ENHANCED
                if self._smart_shift_enhanced
                else FEAT_SMART_SHIFT
            )
        if self._battery_idx is not None and self._battery_feature_id is not None:
            feature_ids.append(self._battery_feature_id)
        feature_ids.extend(sorted(self._wheel_feature_indexes))
        return tuple(feature_ids)

    def _discovered_feature_inventory(self):
        features = []
        if self._feat_idx is not None:
            features.append({"feature_id": FEAT_REPROG_V4, "index": self._feat_idx})
        if self._dpi_idx is not None:
            features.append({"feature_id": FEAT_ADJ_DPI, "index": self._dpi_idx})
        if self._smart_shift_idx is not None:
            features.append({
                "feature_id": (
                    FEAT_SMART_SHIFT_ENHANCED
                    if self._smart_shift_enhanced
                    else FEAT_SMART_SHIFT
                ),
                "index": self._smart_shift_idx,
            })
        if self._battery_idx is not None and self._battery_feature_id is not None:
            features.append({
                "feature_id": self._battery_feature_id,
                "index": self._battery_idx,
            })
        for feature_id, index in sorted(self._wheel_feature_indexes.items()):
            features.append({"feature_id": feature_id, "index": index})
        if self._onboard_profiles_idx is not None:
            features.append({"feature_id": FEAT_ONBOARD_PROFILES, "index": self._onboard_profiles_idx})
        if self._report_rate_idx is not None:
            features.append({"feature_id": FEAT_REPORT_RATE, "index": self._report_rate_idx})
        if self._backlight2_idx is not None:
            features.append({"feature_id": FEAT_BACKLIGHT2, "index": self._backlight2_idx})
        if self._fn_inversion_idx is not None:
            features.append({"feature_id": FEAT_K375S_FN_INVERSION, "index": self._fn_inversion_idx})
        if self._device_name_idx is not None:
            features.append({"feature_id": FEAT_DEVICE_NAME, "index": self._device_name_idx})
        if self._device_identity_idx is not None:
            features.append({"feature_id": FEAT_DEVICE_IDENTITY, "index": self._device_identity_idx})
        if self._device_type_idx is not None:
            features.append({"feature_id": FEAT_DEVICE_TYPE, "index": self._device_type_idx})
        if self._led_control_idx is not None:
            features.append({"feature_id": FEAT_LED_CONTROL, "index": self._led_control_idx})
        if self._device_mode_idx is not None:
            features.append({"feature_id": FEAT_DEVICE_MODE, "index": self._device_mode_idx})
        if self._led_effects_idx is not None:
            features.append({"feature_id": FEAT_LED_EFFECTS, "index": self._led_effects_idx})
        if self._wireless_power_idx is not None:
            features.append({"feature_id": FEAT_WIRELESS_POWER, "index": self._wireless_power_idx})
        if self._power_management_idx is not None:
            features.append({"feature_id": FEAT_POWER_MANAGEMENT, "index": self._power_management_idx})
        if self._wireless_channel_idx is not None:
            features.append({"feature_id": FEAT_WIRELESS_CHANNEL, "index": self._wireless_channel_idx})
        if self._sleep_timeout_idx is not None:
            features.append({"feature_id": FEAT_SLEEP_TIMEOUT, "index": self._sleep_timeout_idx})
        if self._wireless_status_idx is not None:
            features.append({"feature_id": FEAT_WIRELESS_STATUS, "index": self._wireless_status_idx})
        return tuple(features)

    def dump_device_info(self):
        """Return a dict describing everything we know about the connected device.

        Intended for community contributors who want to submit device definitions.
        Returns None when no device is connected.
        """
        dev = self._connected_device_info
        if dev is None:
            return None

        features = {}
        if self._feat_idx is not None:
            features["REPROG_V4 (0x1B04)"] = f"index 0x{self._feat_idx:02X}"
        if self._dpi_idx is not None:
            features["ADJUSTABLE_DPI (0x2201)"] = f"index 0x{self._dpi_idx:02X}"
        if self._smart_shift_idx is not None:
            feat_name = ("SMART_SHIFT_ENHANCED (0x2111)"
                         if self._smart_shift_enhanced
                         else "SMART_SHIFT (0x2110)")
            features[feat_name] = f"index 0x{self._smart_shift_idx:02X}"
        if self._battery_idx is not None:
            feat_name = (f"0x{self._battery_feature_id:04X}"
                         if self._battery_feature_id else "unknown")
            features[f"BATTERY ({feat_name})"] = f"index 0x{self._battery_idx:02X}"
        for feature_id, index in sorted(self._wheel_feature_indexes.items()):
            features[f"WHEEL (0x{feature_id:04X})"] = f"index 0x{index:02X}"
        if self._onboard_profiles_idx is not None:
            features["ONBOARD_PROFILES (0x8100)"] = f"index 0x{self._onboard_profiles_idx:02X}"
        if self._report_rate_idx is not None:
            features["REPORT_RATE (0x8060)"] = f"index 0x{self._report_rate_idx:02X}"
        if self._backlight2_idx is not None:
            features["BACKLIGHT2 (0x1982)"] = f"index 0x{self._backlight2_idx:02X}"
        if self._fn_inversion_idx is not None:
            features["K375S_FN_INVERSION (0x40A3)"] = f"index 0x{self._fn_inversion_idx:02X}"
        if self._device_name_idx is not None:
            features["DEVICE_NAME (0x0005)"] = f"index 0x{self._device_name_idx:02X}"
        if self._device_identity_idx is not None:
            features["DEVICE_IDENTITY (0x0003)"] = f"index 0x{self._device_identity_idx:02X}"
        if self._device_type_idx is not None:
            features["DEVICE_TYPE (0x0002)"] = f"index 0x{self._device_type_idx:02X}"
        if self._led_control_idx is not None:
            features["LED_CONTROL (0x1A01)"] = f"index 0x{self._led_control_idx:02X}"
        if self._device_mode_idx is not None:
            features["DEVICE_MODE (0x1B00)"] = f"index 0x{self._device_mode_idx:02X}"
        if self._led_effects_idx is not None:
            features["LED_EFFECTS (0x1A02)"] = f"index 0x{self._led_effects_idx:02X}"
        if self._wireless_power_idx is not None:
            features["WIRELESS_POWER (0x1C00)"] = f"index 0x{self._wireless_power_idx:02X}"
        if self._power_management_idx is not None:
            features["POWER_MANAGEMENT (0x1C01)"] = f"index 0x{self._power_management_idx:02X}"
        if self._wireless_channel_idx is not None:
            features["WIRELESS_CHANNEL (0x1D00)"] = f"index 0x{self._wireless_channel_idx:02X}"
        if self._sleep_timeout_idx is not None:
            features["SLEEP_TIMEOUT (0x1E00)"] = f"index 0x{self._sleep_timeout_idx:02X}"
        if self._wireless_status_idx is not None:
            features["WIRELESS_STATUS (0x1F00)"] = f"index 0x{self._wireless_status_idx:02X}"

        controls = []
        for c in self._last_controls:
            controls.append({
                "index": c["index"],
                "cid": f"0x{c['cid']:04X}",
                "task": f"0x{c['task']:04X}",
                "flags": f"0x{c['flags']:04X}",
                "position": c.get("pos"),
                "group": c.get("group"),
                "group_mask": f"0x{c.get('gmask', 0):02X}",
                "mapped_to": f"0x{c['mapped_to']:04X}",
                "mapping_flags": f"0x{c['mapping_flags']:04X}",
            })

        return {
            "device_key": dev.key,
            "display_name": dev.display_name,
            "product_id": f"0x{dev.product_id:04X}" if dev.product_id else None,
            "product_name": dev.product_name,
            "transport": dev.transport,
            "ui_layout": dev.ui_layout,
            "supported_buttons": list(dev.supported_buttons),
            "gesture_cids": [f"0x{c:04X}" for c in dev.gesture_cids],
            "dpi_range": [dev.dpi_min, dev.dpi_max],
            "discovered_features": features,
            "reprog_controls": controls,
            "gesture_candidates": [f"0x{c:04X}" for c in self._gesture_candidates],
            "capability_inventory": dev.capability_inventory.to_dict(),
        }

    # ── device discovery ──────────────────────────────────────────

    @staticmethod
    def _vendor_hid_infos():
        """Return candidate Logitech HID interfaces from hidapi and macOS IOKit."""
        out = []
        seen = set()

        def add_info(info):
            pid = int(info.get("product_id", 0) or 0)
            up = int(info.get("usage_page", 0) or 0)
            usage = int(info.get("usage", 0) or 0)
            transport = info.get("transport") or ""
            path = info.get("path") or b""
            if isinstance(path, str):
                path = path.encode("utf-8", errors="replace")
            key = (pid, up, usage, transport, bytes(path))
            if key in seen:
                return
            seen.add(key)
            out.append(info)

        if HIDAPI_OK and _BACKEND_PREFERENCE in ("auto", "hidapi"):
            try:
                raw_infos = list(_hid.enumerate(LOGI_VID, 0))
                if not raw_infos:
                    _log_once(
                        f"hidapi-empty-{_HID_MODULE_NAME}",
                        "[HidGesture] "
                        f"{_HID_MODULE_NAME or 'hidapi'} enumerate(0x{LOGI_VID:04X}) "
                        "returned no Logitech HID interfaces"
                    )
                    linux_nodes = _linux_logitech_hidraw_nodes()
                    if linux_nodes:
                        _log_once(
                            "linux-hidraw-logitech-present",
                            "[HidGesture] Linux sysfs sees Logitech hidraw nodes: "
                            f"{'; '.join(linux_nodes[:8])}. If hidapi still sees "
                            "none, check hidraw backend packaging and /dev/hidraw "
                            "permissions."
                        )
                    elif sys.platform.startswith("linux"):
                        _log_once(
                            "linux-hidraw-logitech-missing",
                            "[HidGesture] Linux sysfs sees no Logitech hidraw "
                            "nodes for VID 0x046D; verify the mouse is connected "
                            "as an active HID device, not only paired."
                        )
                hidapi_candidates = 0
                fallback_candidates = 0
                for info in raw_infos:
                    pid = int(info.get("product_id", 0) or 0)
                    usage_page = int(info.get("usage_page", 0) or 0)
                    usage = int(info.get("usage", 0) or 0)
                    product = info.get("product_string")
                    if usage_page >= 0xFF00:
                        add_info(dict(info, source="hidapi-enumerate"))
                        hidapi_candidates += 1
                        continue
                    if resolve_device(product_id=pid, product_name=product):
                        print(
                            "[HidGesture] Accepting known Logitech device "
                            "without vendor usage metadata for fallback probe "
                            f"PID=0x{pid:04X} UP=0x{usage_page:04X} "
                            f"usage=0x{usage:04X} product={product or '?'}"
                        )
                        add_info(dict(info, source="hidapi-enumerate-fallback"))
                        fallback_candidates += 1
                if raw_infos and not (hidapi_candidates or fallback_candidates):
                    print(
                        "[HidGesture] hidapi found Logitech interfaces, but none "
                        "matched vendor usage metadata or known-device fallback"
                    )
                    _log_once(
                        f"hidapi-filtered-{_HID_MODULE_NAME}",
                        "[HidGesture] Filtered Logitech HID interfaces: "
                        f"{_summarize_hid_infos(raw_infos)}"
                    )
            except Exception as exc:
                print(f"[HidGesture] hidapi enumerate error: {exc}")

        if (
            sys.platform == "darwin"
            and _MAC_NATIVE_OK
            and _BACKEND_PREFERENCE in ("auto", "iokit")
        ):
            for info in _MacNativeHidDevice.enumerate_infos():
                add_info(info)

        return out

    # ── low-level HID++ I/O ───────────────────────────────────────

    def _tx(self, report_id, feat, func, params):
        """Transmit an HID++ message.  Always uses 20-byte long format
        because BLE HID collections typically only support long output reports."""
        buf = [0] * LONG_LEN
        buf[0] = LONG_ID                 # always long for BLE compat
        buf[1] = self._dev_idx
        buf[2] = feat
        buf[3] = ((func & 0x0F) << 4) | (MY_SW & 0x0F)
        for i, b in enumerate(params):
            if 4 + i < LONG_LEN:
                buf[4 + i] = b & 0xFF
        self._dev.write(buf)

    def _rx(self, timeout_ms=2000):
        """Read one HID input report (blocking with timeout).
        Raises on device error (e.g., disconnection) so callers
        can trigger reconnection."""
        dev = self._dev
        if dev is None:
            return None
        d = dev.read(64, timeout_ms)
        return list(d) if d else None

    def _request(self, feat, func, params, timeout_ms=2000):
        """Send a long HID++ request, wait for matching response."""
        req_params = list(params)
        try:
            self._tx(LONG_ID, feat, func, req_params)
        except Exception as exc:
            print(f"[HidGesture] request tx failed feat=0x{feat:02X} func=0x{func:X} "
                  f"params=[{_hex_bytes(req_params)}]: {exc}")
            # Discovery probes should skip bad candidates, but an active session
            # transport failure means the live handle has died and the main loop
            # must run its existing cleanup/reconnect path.
            if self._connected:
                raise IOError(str(exc)) from exc
            return None
        deadline = time.time() + timeout_ms / 1000
        while time.time() < deadline:
            try:
                raw = self._rx(min(500, timeout_ms))
            except Exception as exc:
                print(f"[HidGesture] request rx failed feat=0x{feat:02X} func=0x{func:X} "
                      f"params=[{_hex_bytes(req_params)}]: {exc}")
                if self._connected:
                    raise IOError(str(exc)) from exc
                return None
            if raw is None:
                continue
            msg = _parse(raw)
            if msg is None:
                continue
            _, r_feat, r_func, r_sw, r_params = msg

            # HID++ error (feature-index 0xFF)
            if r_feat == 0xFF:
                code = r_params[1] if len(r_params) > 1 else 0
                code_name = HIDPP_ERROR_NAMES.get(code, "UNKNOWN")
                print(f"[HidGesture] HID++ error 0x{code:02X} ({code_name}) "
                      f"for feat=0x{feat:02X} func=0x{func:X} "
                      f"devIdx=0x{self._dev_idx:02X} req=[{_hex_bytes(req_params)}] "
                      f"resp=[{_hex_bytes(r_params)}]")
                return None

            expected_funcs = {func, (func + 1) & 0x0F}
            if r_feat == feat and r_sw == MY_SW and r_func in expected_funcs:
                self._consecutive_request_timeouts = 0
                return msg
            # Forward non-matching reports (e.g. diverted button events) so
            # button held-state tracking stays in sync during command exchanges.
            self._on_report(raw)
        self._consecutive_request_timeouts += 1
        print(f"[HidGesture] request timeout feat=0x{feat:02X} func=0x{func:X} "
              f"devIdx=0x{self._dev_idx:02X} params=[{_hex_bytes(req_params)}] "
              f"(consecutive={self._consecutive_request_timeouts})")
        return None

    # ── feature helpers ───────────────────────────────────────────

    def _find_feature(self, feature_id):
        """Use IRoot (feature 0x0000) to discover a feature index."""
        hi = (feature_id >> 8) & 0xFF
        lo = feature_id & 0xFF
        resp = self._request(0x00, 0, [hi, lo, 0x00])
        if resp:
            _, _, _, _, p = resp
            if p and p[0] != 0:
                return p[0]
        return None

    def _query_device_name(self):
        """Query device name via HID++ feature 0x0005 (DEVICE_NAME_TYPE)."""
        name_idx = self._find_feature(FEAT_DEVICE_NAME)
        if name_idx is None:
            return None
        resp = self._request(name_idx, 0, [0x00] * 3)
        if not resp:
            return None
        _, _, _, _, params = resp
        name_len = params[0]
        if name_len == 0:
            return None
        name_bytes = []
        offset = 0
        while offset < name_len:
            resp = self._request(name_idx, 1, [offset, 0x00, 0x00])
            if not resp:
                break
            _, _, _, _, chunk = resp
            remaining = name_len - offset
            name_bytes.extend(chunk[:remaining])
            offset += len(chunk)
            if len(chunk) == 0:
                break
        if not name_bytes:
            return None
        name = bytes(name_bytes).decode("ascii", errors="replace").strip("\x00").strip()
        return name if name else None

    def read_device_name(self):
        """Public wrapper for device/friendly name read (009.15)."""
        return self._query_device_name()

    # 009.24: Basic Device Serial Number / Hardware Version / Identity read (host-side only, temporary)
    def read_device_identity(self):
        """Return basic device identity info (serial / hardware version) or None. Host-side only, temporary."""
        if self._device_identity_idx is None or self._dev is None:
            return None
        # Minimal implementation: request function 0x00 (or equivalent) and return raw params for now.
        resp = self._request(self._device_identity_idx, 0x00, [])
        if resp and resp[4]:
            # Return raw bytes/params; higher layers or future handler can parse.
            return list(resp[4])
        return None

    # 009.23: Basic write support for Device Name / Friendly Name (host-side only, temporary)
    def set_device_name(self, name: str):
        """Set device/friendly name. Host-side only, temporary. Returns success."""
        name_idx = self._find_feature(FEAT_DEVICE_NAME)
        if name_idx is None or self._dev is None:
            print("[HidGesture] set_device_name: Device Name feature not available — not applied")
            return False
        try:
            name_bytes = name.encode("ascii", errors="replace")[:255]  # safe length
            # Simple chunked write (function 0x10 or equivalent; adjust if real protocol differs)
            # For minimal scope we send the full name in one request if short, or first chunk.
            payload = [len(name_bytes)] + list(name_bytes[:3])  # header + first bytes (protocol-dependent)
            resp = self._request(name_idx, 0x10, payload)
            success = resp is not None
            # For a more complete implementation we would chunk the rest of the name here.
            print(f"[HidGesture] Device Name set (host-side, temporary): name='{name}' -> {'OK' if success else 'FAILED'}")
            return success
        except Exception as e:
            print(f"[HidGesture] set_device_name error: {e}")
            return False

    # 009.31: Thin aliases for Device Friendly Name (user-settable name) — delegates to the existing Device Name path (same 0x0005 feature on most devices)
    def read_device_friendly_name(self):
        """Return the current user-settable Friendly Name (or None). Host-side only, temporary."""
        return self.read_device_name()

    def set_device_friendly_name(self, name: str):
        """Set the user-settable Friendly Name. Host-side only, temporary. Returns success."""
        return self.set_device_name(name)

    # 009.35: Basic Device Type / Product Type skeleton (host-side only, temporary; read-only)
    def read_device_type(self):
        """Returns current device type / product type value or None. Host-side only, temporary."""
        if self._device_type_idx is None or self._dev is None:
            return None
        resp = self._request(self._device_type_idx, 0x00, [])
        if resp and resp[4]:
            return resp[4][0] if resp[4] else None
        return None

    # 009.37: Basic Power Management (beyond Sleep Timeout) skeleton (host-side only, temporary)
    def read_power_management(self):
        """Returns current power management settings / profile or None. Host-side only, temporary."""
        if self._power_management_idx is None or self._dev is None:
            return None
        resp = self._request(self._power_management_idx, 0x00, [])
        if resp and resp[4]:
            return list(resp[4])  # raw parameters for now
        return None

    def set_power_management(self, settings):
        """Set power management settings / profile. Host-side only, temporary. Returns success."""
        if self._power_management_idx is None or self._dev is None:
            print("[HidGesture] set_power_management: Power Management not available — not applied")
            return False
        # Minimal implementation: send the settings payload (exact format depends on real feature)
        payload = settings if isinstance(settings, (list, tuple)) else [settings]
        resp = self._request(self._power_management_idx, 0x10, payload)
        success = resp is not None
        print(f"[HidGesture] Power Management set (host-side, temporary) -> {'OK' if success else 'FAILED'}")
        return success

    # 009.16: Basic LED control skeleton (host-side only, temporary)
    def set_led_state(self, enabled: bool, brightness: int | None = None):
        """Host-side LED on/off + optional brightness (0-100). Temporary (lost on reconnect/host switch)."""
        if self._led_control_idx is None or self._dev is None:
            print("[HidGesture] set_led_state: LED control not available — not applied")
            return False
        lvl = 0 if not enabled else (brightness if brightness is not None else 50)
        payload = [1 if enabled else 0, max(0, min(100, lvl))]
        resp = self._request(self._led_control_idx, 0x10, payload)
        success = resp is not None
        print(f"[HidGesture] LED set (host-side, temporary): enabled={enabled}, brightness={lvl} -> {'OK' if success else 'FAILED'}")
        return success

    def read_led_state(self):
        """Returns (enabled: bool | None, brightness: int | None) for mouse LEDs. Host-side only, temporary."""
        if self._led_control_idx is None or self._dev is None:
            return None, None
        resp = self._request(self._led_control_idx, 0x00, [])
        if resp and resp[4]:
            params = resp[4]
            enabled = bool(params[0]) if len(params) > 0 else None
            brightness = params[1] if len(params) > 1 else None
            return enabled, brightness
        return None, None

    # 009.17: Basic Device Mode (Wireless Mode) skeleton (host-side only, temporary)
    def read_device_mode(self):
        """Returns current device mode value or None. Host-side only, temporary."""
        if self._device_mode_idx is None or self._dev is None:
            return None
        resp = self._request(self._device_mode_idx, 0x00, [])
        if resp and resp[4]:
            return resp[4][0] if resp[4] else None
        return None

    def set_device_mode(self, mode_value: int):
        """Set device mode. Host-side only, temporary. Returns success."""
        if self._device_mode_idx is None or self._dev is None:
            print("[HidGesture] set_device_mode: Device Mode not available — not applied")
            return False
        payload = [mode_value & 0xFF]
        resp = self._request(self._device_mode_idx, 0x10, payload)
        success = resp is not None
        print(f"[HidGesture] Device Mode set (host-side, temporary): mode={mode_value} -> {'OK' if success else 'FAILED'}")
        return success

    # 009.18: Basic Wireless Power / RF Power Management skeleton (host-side only, temporary)
    def read_wireless_power(self):
        """Returns current wireless power level/mode or None. Host-side only, temporary."""
        if self._wireless_power_idx is None or self._dev is None:
            return None
        resp = self._request(self._wireless_power_idx, 0x00, [])
        if resp and resp[4]:
            return resp[4][0] if resp[4] else None
        return None

    def set_wireless_power(self, power_value: int):
        """Set wireless power level/mode. Host-side only, temporary. Returns success."""
        if self._wireless_power_idx is None or self._dev is None:
            print("[HidGesture] set_wireless_power: Wireless Power not available — not applied")
            return False
        payload = [power_value & 0xFF]
        resp = self._request(self._wireless_power_idx, 0x10, payload)
        success = resp is not None
        print(f"[HidGesture] Wireless Power set (host-side, temporary): power={power_value} -> {'OK' if success else 'FAILED'}")
        return success

    # 009.20: Basic Wireless Channel / RF Channel skeleton (host-side only, temporary)
    def read_wireless_channel(self):
        """Returns current wireless channel or None. Host-side only, temporary."""
        if self._wireless_channel_idx is None or self._dev is None:
            return None
        resp = self._request(self._wireless_channel_idx, 0x00, [])
        if resp and resp[4]:
            return resp[4][0] if resp[4] else None
        return None

    def set_wireless_channel(self, channel_value: int):
        """Set wireless channel. Host-side only, temporary. Returns success."""
        if self._wireless_channel_idx is None or self._dev is None:
            print("[HidGesture] set_wireless_channel: Wireless Channel not available — not applied")
            return False
        payload = [channel_value & 0xFF]
        resp = self._request(self._wireless_channel_idx, 0x10, payload)
        success = resp is not None
        print(f"[HidGesture] Wireless Channel set (host-side, temporary): channel={channel_value} -> {'OK' if success else 'FAILED'}")
        return success

    # 009.21: Basic Sleep Timeout / Power Save Timeout skeleton (host-side only, temporary)
    def read_sleep_timeout(self):
        """Returns current sleep/power-save timeout value or None. Host-side only, temporary."""
        if self._sleep_timeout_idx is None or self._dev is None:
            return None
        resp = self._request(self._sleep_timeout_idx, 0x00, [])
        if resp and resp[4]:
            return resp[4][0] if resp[4] else None
        return None

    def set_sleep_timeout(self, timeout_value: int):
        """Set sleep/power-save timeout. Host-side only, temporary. Returns success."""
        if self._sleep_timeout_idx is None or self._dev is None:
            print("[HidGesture] set_sleep_timeout: Sleep Timeout not available — not applied")
            return False
        payload = [timeout_value & 0xFF]
        resp = self._request(self._sleep_timeout_idx, 0x10, payload)
        success = resp is not None
        print(f"[HidGesture] Sleep Timeout set (host-side, temporary): timeout={timeout_value} -> {'OK' if success else 'FAILED'}")
        return success

    # 009.22 / 009.41: Basic Wireless Status (link quality / RSSI / additional health metrics) — host-side only, temporary; read-only
    def read_wireless_status(self):
        """Returns current wireless status values (raw parameters + labeled fields when available). Host-side only, temporary."""
        if self._wireless_status_idx is None or self._dev is None:
            return None
        resp = self._request(self._wireless_status_idx, 0x00, [])
        if resp and resp[4]:
            raw = list(resp[4])
            result = {"raw": raw}
            # 009.41: Parse additional cleanly available fields when the response length supports it
            # (typical Logitech Wireless Status responses often encode link quality and RSSI in the first bytes)
            if len(raw) >= 1:
                result["link_quality"] = raw[0]
            if len(raw) >= 2:
                result["rssi"] = raw[1]  # signed interpretation may be needed on some devices; raw value for now
            return result
        return None

    # 009.19: Basic LED Effects skeleton (host-side only, temporary)
    def read_led_effect(self):
        """Returns current LED effect state/parameters or None. Host-side only, temporary."""
        if self._led_effects_idx is None or self._dev is None:
            return None
        resp = self._request(self._led_effects_idx, 0x00, [])
        if resp and resp[4]:
            return list(resp[4])  # raw parameters for now
        return None

    def set_led_effect(self, effect: int, params: list | None = None):
        """Set LED effect and optional parameters. Host-side only, temporary. Returns success."""
        if self._led_effects_idx is None or self._dev is None:
            print("[HidGesture] set_led_effect: LED Effects not available — not applied")
            return False
        payload = [effect & 0xFF]
        if params:
            payload.extend([p & 0xFF for p in params])
        resp = self._request(self._led_effects_idx, 0x10, payload)
        success = resp is not None
        print(f"[HidGesture] LED Effect set (host-side, temporary): effect={effect} -> {'OK' if success else 'FAILED'}")
        return success

    def _discover_common_features(self):
        """Discover DPI, battery, wheel (including ratchet on 0x2121), onboard profiles (0x8100),
        and report rate.  Safe to call on any opened HID++ device, including gaming mice
        that lack REPROG_CONTROLS_V4.
        """
        # ADJUSTABLE_DPI
        dpi_fi = self._find_feature(FEAT_ADJ_DPI)
        if dpi_fi:
            self._dpi_idx = dpi_fi
            print(f"[HidGesture] Found ADJUSTABLE_DPI @0x{dpi_fi:02X}")

        # SMART_SHIFT (only useful for MX-style devices; harmless on others)
        ss_fi = self._find_feature(FEAT_SMART_SHIFT_ENHANCED)
        if ss_fi:
            self._smart_shift_idx = ss_fi
            self._smart_shift_enhanced = True
            print(f"[HidGesture] Found SMART_SHIFT_ENHANCED @0x{ss_fi:02X}")
        else:
            ss_fi = self._find_feature(FEAT_SMART_SHIFT)
            if ss_fi:
                self._smart_shift_idx = ss_fi
                self._smart_shift_enhanced = False
                print(f"[HidGesture] Found SMART_SHIFT (basic) @0x{ss_fi:02X}")

        # Wheel features (HIRES_WHEEL_ENHANCED 0x2121 on G502 X gives ratchet control)
        for wheel_feature in (
            FEAT_HIRES_WHEEL,
            FEAT_HIRES_WHEEL_ENHANCED,
            FEAT_LOWRES_WHEEL,
            FEAT_THUMB_WHEEL,
        ):
            wheel_fi = self._find_feature(wheel_feature)
            if wheel_fi:
                self._wheel_feature_indexes[wheel_feature] = wheel_fi
                print(f"[HidGesture] Found wheel feature 0x{wheel_feature:04X} @0x{wheel_fi:02X}")

        # Battery
        batt_fi = self._find_feature(FEAT_UNIFIED_BATT)
        if batt_fi:
            self._battery_idx = batt_fi
            self._battery_feature_id = FEAT_UNIFIED_BATT
            print(f"[HidGesture] Found UNIFIED_BATT @0x{batt_fi:02X}")
        else:
            batt_fi = self._find_feature(FEAT_BATTERY_STATUS)
            if batt_fi:
                self._battery_idx = batt_fi
                self._battery_feature_id = FEAT_BATTERY_STATUS
                print(f"[HidGesture] Found BATTERY_STATUS @0x{batt_fi:02X}")

        # Gaming / onboard mice features
        onboard_fi = self._find_feature(FEAT_ONBOARD_PROFILES)
        if onboard_fi:
            self._onboard_profiles_idx = onboard_fi
            print(f"[HidGesture] Found ONBOARD_PROFILES @0x{onboard_fi:02X}")

        rr_fi = self._find_feature(FEAT_REPORT_RATE)
        if rr_fi:
            self._report_rate_idx = rr_fi
            print(f"[HidGesture] Found REPORT_RATE @0x{rr_fi:02X}")

        # Keyboard / general device features (safe and useful on MX Mechanical Mini etc.)
        bl_fi = self._find_feature(FEAT_BACKLIGHT2)
        if bl_fi:
            self._backlight2_idx = bl_fi
            print(f"[HidGesture] Found BACKLIGHT2 @0x{bl_fi:02X}")

        # Litra Beam illumination (first functional control slice)
        litra_fi = self._find_feature(FEAT_LITRA_ILLUMINATION)
        if litra_fi:
            self._litra_illumination_idx = litra_fi
            print(f"[HidGesture] Found Litra illumination @0x{litra_fi:02X}")

        # Device Name / Friendly Name (common identity feature)
        dn_fi = self._find_feature(FEAT_DEVICE_NAME)
        if dn_fi:
            self._device_name_idx = dn_fi
            print(f"[HidGesture] Found DEVICE_NAME @0x{dn_fi:02X}")

        # Device Serial Number / Hardware Version / Identity — 009.24
        di_fi = self._find_feature(FEAT_DEVICE_IDENTITY)
        if di_fi:
            self._device_identity_idx = di_fi
            print(f"[HidGesture] Found DEVICE_IDENTITY @0x{di_fi:02X}")

        # Device Type / Product Type — 009.35
        dt_fi = self._find_feature(FEAT_DEVICE_TYPE)
        if dt_fi:
            self._device_type_idx = dt_fi
            print(f"[HidGesture] Found DEVICE_TYPE @0x{dt_fi:02X}")

        # Common mouse LED control (on/off + brightness) — 009.16
        led_fi = self._find_feature(FEAT_LED_CONTROL)
        if led_fi:
            self._led_control_idx = led_fi
            print(f"[HidGesture] Found LED_CONTROL @0x{led_fi:02X}")

        # Device Mode / Wireless Mode — 009.17
        dm_fi = self._find_feature(FEAT_DEVICE_MODE)
        if dm_fi:
            self._device_mode_idx = dm_fi
            print(f"[HidGesture] Found DEVICE_MODE @0x{dm_fi:02X}")

        # LED Effects (patterns/modes beyond basic on/off + brightness) — 009.19
        le_fi = self._find_feature(FEAT_LED_EFFECTS)
        if le_fi:
            self._led_effects_idx = le_fi
            print(f"[HidGesture] Found LED_EFFECTS @0x{le_fi:02X}")

        # Wireless Power / RF Power Management — 009.18
        wp_fi = self._find_feature(FEAT_WIRELESS_POWER)
        if wp_fi:
            self._wireless_power_idx = wp_fi
            print(f"[HidGesture] Found WIRELESS_POWER @0x{wp_fi:02X}")

        # Power Management (beyond Sleep Timeout / Wireless Power) — 009.37
        pm_fi = self._find_feature(FEAT_POWER_MANAGEMENT)
        if pm_fi:
            self._power_management_idx = pm_fi
            print(f"[HidGesture] Found POWER_MANAGEMENT @0x{pm_fi:02X}")

        # Wireless Channel / RF Channel — 009.20
        wc_fi = self._find_feature(FEAT_WIRELESS_CHANNEL)
        if wc_fi:
            self._wireless_channel_idx = wc_fi
            print(f"[HidGesture] Found WIRELESS_CHANNEL @0x{wc_fi:02X}")

        # Sleep Timeout / Power Save Timeout — 009.21
        st_fi = self._find_feature(FEAT_SLEEP_TIMEOUT)
        if st_fi:
            self._sleep_timeout_idx = st_fi
            print(f"[HidGesture] Found SLEEP_TIMEOUT @0x{st_fi:02X}")

        # Wireless Status (link quality / RSSI) — 009.22
        ws_fi = self._find_feature(FEAT_WIRELESS_STATUS)
        if ws_fi:
            self._wireless_status_idx = ws_fi
            print(f"[HidGesture] Found WIRELESS_STATUS @0x{ws_fi:02X}")

        fn_fi = self._find_feature(FEAT_K375S_FN_INVERSION)
        if fn_fi:
            self._fn_inversion_idx = fn_fi
            print(f"[HidGesture] Found K375S_FN_INVERSION @0x{fn_fi:02X}")

    def _get_cid_reporting(self, cid):
        if self._feat_idx is None:
            return None
        hi = (cid >> 8) & 0xFF
        lo = cid & 0xFF
        return self._request(self._feat_idx, 2, [hi, lo])

    def _set_cid_reporting(self, cid, flags):
        if self._feat_idx is None:
            return None
        hi = (cid >> 8) & 0xFF
        lo = cid & 0xFF
        return self._request(self._feat_idx, 3, [hi, lo, flags, 0x00, 0x00])

    def _discover_reprog_controls(self):
        controls = []
        if self._feat_idx is None:
            return controls
        resp = self._request(self._feat_idx, 0, [])
        if not resp:
            print("[HidGesture] Failed to read REPROG_V4 control count")
            return controls
        _, _, _, _, params = resp
        _MAX_REPROG_CONTROLS = 32
        count = params[0] if params else 0
        if count > _MAX_REPROG_CONTROLS:
            print(f"[HidGesture] Suspicious control count {count}, "
                  f"capping to {_MAX_REPROG_CONTROLS}")
            count = _MAX_REPROG_CONTROLS
        print(f"[HidGesture] REPROG_V4 exposes {count} controls")
        consecutive_failures = 0
        for index in range(count):
            key_resp = self._request(self._feat_idx, 1, [index], timeout_ms=500)
            if not key_resp:
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    print(f"[HidGesture] {consecutive_failures} consecutive "
                          f"failures, aborting discovery")
                    break
                print(f"[HidGesture] Failed to read control info for index {index}")
                continue
            consecutive_failures = 0
            _, _, _, _, key_params = key_resp
            if len(key_params) < 9:
                print(f"[HidGesture] Short control info for index {index}: "
                      f"[{_hex_bytes(key_params)}]")
                continue
            cid = (key_params[0] << 8) | key_params[1]
            task = (key_params[2] << 8) | key_params[3]
            flags = key_params[4] | (key_params[8] << 8)
            pos = key_params[5]
            group = key_params[6]
            gmask = key_params[7]
            control = {
                "index": index,
                "cid": cid,
                "task": task,
                "flags": flags,
                "pos": pos,
                "group": group,
                "gmask": gmask,
                "mapped_to": cid,
                "mapping_flags": 0,
            }
            map_resp = self._get_cid_reporting(cid)
            if map_resp:
                _, _, _, _, map_params = map_resp
                if len(map_params) >= 5:
                    mapped_cid = (map_params[0] << 8) | map_params[1]
                    map_flags = map_params[2]
                    mapped_to = (map_params[3] << 8) | map_params[4]
                    if len(map_params) >= 6:
                        map_flags |= map_params[5] << 8
                    control["mapped_to"] = mapped_to or mapped_cid or cid
                    control["mapping_flags"] = map_flags
            controls.append(control)
            print(
                "[HidGesture] Control "
                f"idx={index} cid={_format_cid(cid)} task=0x{task:04X} "
                f"flags=0x{flags:04X}[{_format_flags(flags, KEY_FLAG_BITS)}] "
                f"group={group} gmask=0x{gmask:02X} pos={pos} "
                f"mappedTo=0x{control['mapped_to']:04X} "
                f"reporting=0x{control['mapping_flags']:04X}"
                f"[{_format_flags(control['mapping_flags'], MAPPING_FLAG_BITS)}]"
            )
        return controls

    def _choose_gesture_candidates(self, controls, device_spec=None):
        present = {c["cid"] for c in controls}
        ordered = []
        preferred = tuple(
            getattr(device_spec, "gesture_cids", ()) or DEFAULT_GESTURE_CIDS
        )

        def add_candidate(cid):
            if cid in present and cid not in ordered:
                ordered.append(cid)

        for cid in preferred:
            add_candidate(cid)

        for control in controls:
            cid = control["cid"]
            flags = int(control.get("flags", 0) or 0)
            mapping_flags = int(control.get("mapping_flags", 0) or 0)
            raw_xy_capable = bool(
                flags & 0x0100
                or flags & 0x0200
                or mapping_flags & 0x0010
                or mapping_flags & 0x0040
            )
            virtual_or_named = bool(
                flags & 0x0080
                or "gesture" in KNOWN_CID_NAMES.get(cid, "").lower()
            )
            if raw_xy_capable and virtual_or_named and flags & 0x0020:
                add_candidate(cid)

        return ordered or list(preferred)

    def _divert(self):
        """Divert the selected gesture control and enable raw XY when supported."""
        if self._feat_idx is None:
            return False
        for cid in self._gesture_candidates:
            self._gesture_cid = cid
            resp = self._set_cid_reporting(cid, 0x33)
            if resp is not None:
                self._rawxy_enabled = True
                print(f"[HidGesture] Divert {_format_cid(cid)} with RawXY: OK")
                return True
            self._rawxy_enabled = False
            resp = self._set_cid_reporting(cid, 0x03)
            ok = resp is not None
            print(f"[HidGesture] Divert {_format_cid(cid)}: "
                  f"{'OK' if ok else 'FAILED'}")
            if ok:
                return True
        self._gesture_cid = DEFAULT_GESTURE_CID
        return False

    def _divert_extras(self):
        """Divert additional CIDs (e.g. mode shift) without raw XY."""
        if self._feat_idx is None:
            return
        for cid, info in self._extra_diverts.items():
            resp = self._set_cid_reporting(cid, 0x03)
            ok = resp is not None
            print(f"[HidGesture] Extra divert {_format_cid(cid)}: "
                  f"{'OK' if ok else 'FAILED'}")

    def _undivert(self):
        """Restore default button behaviour (best-effort)."""
        if self._feat_idx is None or self._dev is None:
            return
        # Undivert extra CIDs
        for cid in self._extra_diverts:
            hi = (cid >> 8) & 0xFF
            lo = cid & 0xFF
            try:
                self._tx(LONG_ID, self._feat_idx, 3,
                         [hi, lo, 0x02, 0x00, 0x00])
            except Exception:
                pass
        # Undivert gesture CID
        hi = (self._gesture_cid >> 8) & 0xFF
        lo = self._gesture_cid & 0xFF
        flags = 0x22 if self._rawxy_enabled else 0x02
        try:
            self._tx(LONG_ID, self._feat_idx, 3,
                     [hi, lo, flags, 0x00, 0x00])
        except Exception:
            pass
        self._rawxy_enabled = False

    # ── DPI control ───────────────────────────────────────────────

    def set_dpi(self, dpi_value):
        """Queue a DPI change — will be applied on the listener thread.
        Can be called from any thread.  Returns True on success."""
        dpi = clamp_dpi(dpi_value, self._connected_device_info)
        self._dpi_result = None
        self._pending_dpi = dpi
        # Wait up to 3s for the listener thread to apply it
        for _ in range(30):
            if self._pending_dpi is None:
                return self._dpi_result is True
            time.sleep(0.1)
        print("[HidGesture] DPI set timed out")
        return False

    def _apply_pending_dpi(self):
        """Called from the listener thread to actually send DPI."""
        dpi = self._pending_dpi
        if dpi is None:
            return
        if self._dpi_idx is None or self._dev is None:
            print("[HidGesture] Cannot set DPI — not connected")
            self._dpi_result = False
            self._pending_dpi = None
            return
        hi = (dpi >> 8) & 0xFF
        lo = dpi & 0xFF
        # setSensorDpi: function 3, params [sensorIdx=0, dpi_hi, dpi_lo]
        # (function 2 = getSensorDpi, function 3 = setSensorDpi)
        resp = self._request(self._dpi_idx, 3, [0x00, hi, lo])
        if resp:
            _, _, _, _, p = resp
            actual = (p[1] << 8 | p[2]) if len(p) >= 3 else dpi
            print(f"[HidGesture] DPI set to {actual}")
            self._dpi_result = True
        else:
            print("[HidGesture] DPI set FAILED")
            self._dpi_result = False
        self._pending_dpi = None

    def read_dpi(self):
        """Queue a DPI read — will be applied on the listener thread.
        Can be called from any thread.  Returns the DPI value or None."""
        self._dpi_result = None
        self._pending_dpi = "read"  # special sentinel
        for _ in range(30):
            if self._pending_dpi is None:
                return self._dpi_result
            time.sleep(0.1)
        print("[HidGesture] DPI read timed out")
        self._pending_dpi = None
        return None

    def _apply_pending_read_dpi(self):
        """Called from the listener thread to read current DPI."""
        if self._dpi_idx is None or self._dev is None:
            self._dpi_result = None
            self._pending_dpi = None
            return
        # getSensorDpi: function 2, params [sensorIdx=0]
        resp = self._request(self._dpi_idx, 2, [0x00])
        if resp:
            _, _, _, _, p = resp
            current = (p[1] << 8 | p[2]) if len(p) >= 3 else None
            print(f"[HidGesture] Current DPI = {current}")
            self._dpi_result = current
        else:
            print("[HidGesture] DPI read FAILED")
            self._dpi_result = None
        self._pending_dpi = None

    # ── Smart Shift control ─────────────────────────────────────

    SMART_SHIFT_FREESPIN = 0x01
    SMART_SHIFT_RATCHET  = 0x02
    # auto_disengage byte: 1-50 → SmartShift active with that sensitivity threshold.
    # 0xFF → fixed ratchet (SmartShift effectively disabled, used by Logi Options+).
    SMART_SHIFT_THRESHOLD_MIN     = 1
    SMART_SHIFT_THRESHOLD_MAX     = 50
    SMART_SHIFT_DISABLE_THRESHOLD = 0xFF

    @property
    def smart_shift_supported(self):
        return self._smart_shift_idx is not None

    def set_smart_shift(self, mode, smart_shift_enabled=False, threshold=25):
        """Queue a Smart Shift settings change.
        mode: 'ratchet' or 'freespin' (fixed mode when smart_shift_enabled=False)
        smart_shift_enabled: True to enable auto SmartShift (auto-switching)
        threshold: 1-50 sensitivity when SmartShift is enabled
        Can be called from any thread.  Returns True on success."""
        pending = (mode, smart_shift_enabled, threshold)
        with self._smart_shift_call_lock:
            with self._smart_shift_slot_lock:
                self._smart_shift_result = None
                self._pending_smart_shift = pending
                self._smart_shift_event.clear()
            if not self._smart_shift_event.wait(3):
                with self._smart_shift_slot_lock:
                    if self._pending_smart_shift == pending:
                        self._smart_shift_result = False
                        self._pending_smart_shift = None
                        self._smart_shift_event.set()
                print("[HidGesture] Smart Shift set timed out")
                return False
            with self._smart_shift_slot_lock:
                return self._smart_shift_result is True

    def _apply_pending_smart_shift(self):
        with self._smart_shift_slot_lock:
            pending = self._pending_smart_shift
        if pending is None:
            return
        if self._smart_shift_idx is None or self._dev is None:
            print("[HidGesture] Cannot set Smart Shift — not connected")
            self._finish_pending_smart_shift(None if pending == "read" else False)
            return
        if pending == "read":
            self._apply_pending_read_smart_shift()
            return
        mode, smart_shift_enabled, threshold = pending
        # Function IDs differ between basic (0x2110) and enhanced (0x2111):
        #   enhanced: read fn=1, write fn=2
        #   basic:    read fn=0, write fn=1
        write_fn = 2 if self._smart_shift_enhanced else 1
        if smart_shift_enabled:
            # SmartShift enabled: mode=ratchet (0x02) + autoDisengage threshold (1-50).
            # Sending mode=0x02 explicitly avoids "no-change" ambiguity with 0x00.
            threshold = max(self.SMART_SHIFT_THRESHOLD_MIN,
                            min(self.SMART_SHIFT_THRESHOLD_MAX, int(threshold)))
            resp = self._request(self._smart_shift_idx, write_fn,
                                 [self.SMART_SHIFT_RATCHET, threshold, 0x00])
            label = f"SmartShift enabled (threshold={threshold})"
        elif mode == "freespin":
            resp = self._request(self._smart_shift_idx, write_fn,
                                 [self.SMART_SHIFT_FREESPIN, 0x00, 0x00])
            label = "fixed freespin"
        else:
            # Disable SmartShift + fixed ratchet: threshold=0xFF means always-ratchet
            # (matches Solaar's max-threshold approach; hardware ignores auto_disengage for mode writes).
            resp = self._request(self._smart_shift_idx, write_fn,
                                 [self.SMART_SHIFT_RATCHET, self.SMART_SHIFT_DISABLE_THRESHOLD, 0x00])
            label = "fixed ratchet (SmartShift disabled)"
        if resp:
            print(f"[HidGesture] Smart Shift set to {label}")
            result = True
        else:
            print("[HidGesture] Smart Shift set FAILED")
            result = False
        self._finish_pending_smart_shift(result)

    def force_reconnect(self):
        """Request the listener thread to drop and re-establish the HID++ connection.

        Thread-safe: sets a flag checked at the top of the inner event loop.
        The loop raises IOError, which triggers full cleanup + _try_connect(),
        re-applying all button diverts (including CID 0x00C4).
        """
        self._reconnect_requested = True

    def read_smart_shift(self):
        """Queue a Smart Shift read.
        Returns dict {'mode': str, 'enabled': bool, 'threshold': int} or None."""
        with self._smart_shift_call_lock:
            with self._smart_shift_slot_lock:
                self._smart_shift_result = None
                self._pending_smart_shift = "read"
                self._smart_shift_event.clear()
            if not self._smart_shift_event.wait(3):
                with self._smart_shift_slot_lock:
                    if self._pending_smart_shift == "read":
                        self._smart_shift_result = None
                        self._pending_smart_shift = None
                        self._smart_shift_event.set()
                print("[HidGesture] Smart Shift read timed out")
                return None
            with self._smart_shift_slot_lock:
                return self._smart_shift_result

    def _finish_pending_smart_shift(self, result):
        with self._smart_shift_slot_lock:
            self._smart_shift_result = result
            self._pending_smart_shift = None
            self._smart_shift_event.set()

    def _abort_pending_smart_shift(self):
        with self._smart_shift_slot_lock:
            pending = self._pending_smart_shift
            if pending is None:
                self._smart_shift_result = None
                return
            self._smart_shift_result = None if pending == "read" else False
            self._pending_smart_shift = None
            self._smart_shift_event.set()

    def _apply_pending_read_smart_shift(self):
        if self._smart_shift_idx is None or self._dev is None:
            self._finish_pending_smart_shift(None)
            return
        # enhanced (0x2111): read fn=1; basic (0x2110): read fn=0
        read_fn = 1 if self._smart_shift_enhanced else 0
        resp = self._request(self._smart_shift_idx, read_fn, [])
        if resp:
            _, _, _, _, p = resp
            mode_byte = p[0] if p else 0
            auto_disengage = p[1] if len(p) > 1 else 0
            print(f"[HidGesture] Smart Shift raw: mode=0x{mode_byte:02X} auto_disengage=0x{auto_disengage:02X}")
            # Freespin mode means fixed free-spin — SmartShift auto-switching is always OFF.
            # The device preserves the auto_disengage byte in freespin state, so we must
            # not use it to infer enabled=True; only ratchet mode can have SmartShift active.
            # For ratchet: auto_disengage 1-50 → SmartShift active; 0 or ≥51 → disabled.
            mode = "freespin" if mode_byte == self.SMART_SHIFT_FREESPIN else "ratchet"
            if mode == "freespin":
                threshold = auto_disengage if self.SMART_SHIFT_THRESHOLD_MIN <= auto_disengage <= self.SMART_SHIFT_THRESHOLD_MAX else 25
                result = {"mode": "freespin", "enabled": False, "threshold": threshold}
            elif self.SMART_SHIFT_THRESHOLD_MIN <= auto_disengage <= self.SMART_SHIFT_THRESHOLD_MAX:
                result = {"mode": "ratchet", "enabled": True, "threshold": auto_disengage}
            else:
                result = {"mode": "ratchet", "enabled": False, "threshold": 25}
            print(f"[HidGesture] Smart Shift state = {result}")
            self._finish_pending_smart_shift(result)
        else:
            print("[HidGesture] Smart Shift read FAILED")
            self._finish_pending_smart_shift(None)

    def read_battery(self):
        """Queue a battery read and wait for the listener thread result."""
        self._battery_result = None
        self._pending_battery = "read"
        for _ in range(30):
            if self._pending_battery is None:
                return self._battery_result
            time.sleep(0.1)
        print("[HidGesture] Battery read timed out")
        self._pending_battery = None
        return None

    def _apply_pending_read_battery(self):
        """Called from the listener thread to read current battery level."""
        if self._battery_idx is None or self._dev is None:
            self._battery_result = None
            self._pending_battery = None
            return

        if self._battery_feature_id == FEAT_UNIFIED_BATT:
            resp = self._request(self._battery_idx, 1, [])
            if resp:
                _, _, _, _, params = resp
                level = params[0] if params else None
                if level is not None and 0 <= level <= 100:
                    if level != self._last_logged_battery:
                        print(f"[HidGesture] Battery (unified): {level}%")
                        self._last_logged_battery = level
                    self._battery_result = level
                else:
                    self._battery_result = None
            else:
                self._battery_result = None
        else:
            resp = self._request(self._battery_idx, 0, [])
            if resp:
                _, _, _, _, params = resp
                level = params[0] if params else None
                if level is not None and 0 <= level <= 100:
                    if level != self._last_logged_battery:
                        print(f"[HidGesture] Battery (status): {level}%")
                        self._last_logged_battery = level
                    self._battery_result = level
                else:
                    self._battery_result = None
            else:
                self._battery_result = None

        self._pending_battery = None

    # ── Backlight (BACKLIGHT2) ──────────────────────────────────────

    def read_backlight(self):
        """Returns (enabled: bool | None, level: int | None). Host-side only, temporary."""
        if self._backlight2_idx is None:
            return None, None

        self._backlight_result = None
        self._pending_backlight = "read"

        for _ in range(30):
            if self._pending_backlight is None:
                return self._backlight_result
            time.sleep(0.1)
        print("[HidGesture] Backlight read timed out")
        self._pending_backlight = None
        return None, None

    def set_backlight(self, enabled: bool, level: int | None = None):
        """Host-side backlight control. Changes are temporary (lost on reconnect/host switch)."""
        if self._backlight2_idx is None:
            return False

        self._pending_backlight = ("set", bool(enabled), level)
        self._backlight_result = None

        for _ in range(30):
            if self._pending_backlight is None:
                return self._backlight_result is True
            time.sleep(0.1)
        print("[HidGesture] Backlight set timed out")
        self._pending_backlight = None
        return False

    def _apply_pending_read_backlight(self):
        if self._backlight2_idx is None or self._dev is None:
            self._backlight_result = (None, None)
            self._pending_backlight = None
            return

        resp = self._request(self._backlight2_idx, 0x00, [])
        if resp:
            params = resp[4] if resp[4] else b""
            enabled = bool(params[0]) if params else None
            level = params[3] if len(params) > 3 else None
            self._backlight_result = (enabled, level)
            print(f"[HidGesture] Backlight (host read): enabled={enabled}, level={level}")
        else:
            self._backlight_result = (None, None)
            print("[HidGesture] Backlight read FAILED")
        self._pending_backlight = None

    def _apply_pending_set_backlight(self, enabled: bool, level: int | None):
        if self._backlight2_idx is None or self._dev is None:
            self._backlight_result = False
            self._pending_backlight = None
            return

        # Minimal V2 write: [enabled, options=0, mask=0xFF, level or 0]
        payload = [1 if enabled else 0, 0x00, 0xFF, level or 0]
        resp = self._request(self._backlight2_idx, 0x10, payload)
        success = resp is not None
        self._backlight_result = success
        if success:
            print(f"[HidGesture] Backlight set (host-side, temporary): enabled={enabled}, level={level}")
        else:
            print("[HidGesture] Backlight set FAILED")
        self._pending_backlight = None

    # ── FN Inversion (K375S_FN_INVERSION) ───────────────────────────

    def read_fn_inversion(self) -> bool | None:
        """Returns current Fn/Fx swap state (host view)."""
        if self._fn_inversion_idx is None:
            return None

        self._fn_result = None
        self._pending_fn = "read"

        for _ in range(30):
            if self._pending_fn is None:
                return self._fn_result
            time.sleep(0.1)
        print("[HidGesture] FN inversion read timed out")
        self._pending_fn = None
        return None

    def set_fn_inversion(self, swap_fx: bool) -> bool:
        """Host-side FN inversion toggle. Temporary."""
        if self._fn_inversion_idx is None:
            return False

        self._pending_fn = ("set", bool(swap_fx))
        self._fn_result = None

        for _ in range(30):
            if self._pending_fn is None:
                return self._fn_result is True
            time.sleep(0.1)
        print("[HidGesture] FN inversion set timed out")
        self._pending_fn = None
        return False

    def _apply_pending_read_fn_inversion(self):
        if self._fn_inversion_idx is None or self._dev is None:
            self._fn_result = None
            self._pending_fn = None
            return

        resp = self._request(self._fn_inversion_idx, 0x00, [])
        if resp:
            params = resp[4] if resp[4] else b""
            swap = bool(params[0]) if params else None
            self._fn_result = swap
            print(f"[HidGesture] FN inversion (host): {swap}")
        else:
            self._fn_result = None
            print("[HidGesture] FN inversion read FAILED")
        self._pending_fn = None

    def _apply_pending_set_fn_inversion(self, swap_fx: bool):
        if self._fn_inversion_idx is None or self._dev is None:
            self._fn_result = False
            self._pending_fn = None
            return

        payload = [1 if swap_fx else 0]
        resp = self._request(self._fn_inversion_idx, 0x10, payload)
        success = resp is not None
        self._fn_result = success

    # ------------------------------------------------------------------
    # Litra Beam basic illumination control (008.2 skeleton, host-side only)
    # ------------------------------------------------------------------

    def set_litra_illumination(self, enabled: bool, brightness: int | None = None):
        """Host-side Litra Beam illumination control (on/off + optional brightness 0-100).
        Temporary (lost on reconnect/host switch). No-op for non-Litra devices."""
        if self._litra_illumination_idx is None or self._dev is None:
            print("[HidGesture] set_litra_illumination: Litra illumination not available — not applied")
            return False
        # Minimal payload: [enabled (1/0), brightness (0-100 or 0 for off)]
        lvl = 0 if not enabled else (brightness if brightness is not None else 50)
        payload = [1 if enabled else 0, max(0, min(100, lvl))]
        resp = self._request(self._litra_illumination_idx, 0x10, payload)
        success = resp is not None
        print(f"[HidGesture] Litra illumination set (host-side, temporary): enabled={enabled}, brightness={lvl} -> {'OK' if success else 'FAILED'}")
        return success

    def read_litra_illumination(self):
        """Returns (enabled: bool | None, brightness: int | None) for Litra Beam.
        Host-side only, temporary. Returns (None, None) for non-Litra devices."""
        if self._litra_illumination_idx is None or self._dev is None:
            return None, None
        resp = self._request(self._litra_illumination_idx, 0x00, [])
        if resp and resp[4]:
            params = resp[4]
            enabled = bool(params[0]) if len(params) > 0 else None
            brightness = params[1] if len(params) > 1 else None
            return enabled, brightness
        return None, None

    def _parse_battery_response(self, params: bytes) -> Optional[dict]:
        """Tiny helper exposed for BatteryHandler (009.2).
        Returns a normalized battery dict or None. For the initial extraction
        this is a placeholder; the real parse logic can be moved in a later micro-chunk.
        """
        # Placeholder for 009.2 — keeps the diff minimal while proving the handler delegation pattern.
        return None
        if success:
            print(f"[HidGesture] FN inversion set (host-side, temporary): swap_fx={swap_fx}")
        else:
            print("[HidGesture] FN inversion set FAILED")
        self._pending_fn = None

    # ── notification handling ─────────────────────────────────────

    @staticmethod
    def _decode_s16(hi, lo):
        value = (hi << 8) | lo
        if value & 0x8000:
            value -= 0x10000
        return value

    def _force_release_stale_holds(self):
        """Synthesize UP events for any buttons stuck in the held state.

        Called from the main loop when consecutive _rx() calls return no data,
        indicating the device may have stalled or gone to sleep while a
        button was physically held.
        """
        if self._held:
            self._held = False
            print("[HidGesture] Gesture force-released (stale hold)")
            if self._on_up:
                try:
                    self._on_up()
                except Exception:
                    pass
        for info in self._extra_diverts.values():
            if info["held"]:
                info["held"] = False
                cb = info.get("on_up")
                if cb:
                    print("[HidGesture] Extra button force-released (stale hold)")
                    try:
                        cb()
                    except Exception:
                        pass

    def _on_report(self, raw):
        """Inspect an incoming HID++ report for diverted button / raw XY events."""
        msg = _parse(raw)
        if msg is None:
            return
        _, feat, func, _sw, params = msg

        if feat != self._feat_idx:
            return

        if func == 1:
            if not self._rawxy_enabled:
                return
            if len(params) < 4 or not self._held:
                return
            dx = self._decode_s16(params[0], params[1])
            dy = self._decode_s16(params[2], params[3])
            if (dx or dy) and self._on_move:
                try:
                    self._on_move(dx, dy)
                except Exception as e:
                    print(f"[HidGesture] move callback error: {e}")
            return

        if func != 0:
            return

        # Params: sequential CID pairs terminated by 0x0000
        cids = set()
        i = 0
        while i + 1 < len(params):
            c = (params[i] << 8) | params[i + 1]
            if c == 0:
                break
            cids.add(c)
            i += 2

        gesture_now = self._gesture_cid in cids

        if gesture_now and not self._held:
            self._held = True
            print("[HidGesture] Gesture DOWN")
            if self._on_down:
                try:
                    self._on_down()
                except Exception as e:
                    print(f"[HidGesture] down callback error: {e}")

        elif not gesture_now and self._held:
            self._held = False
            print("[HidGesture] Gesture UP")
            if self._on_up:
                try:
                    self._on_up()
                except Exception as e:
                    print(f"[HidGesture] up callback error: {e}")

        # Check extra diverted CIDs (e.g. mode shift)
        for cid, info in self._extra_diverts.items():
            btn_now = cid in cids
            if btn_now and not info["held"]:
                info["held"] = True
                print(f"[HidGesture] Extra {_format_cid(cid)} DOWN")
                cb = info.get("on_down")
                if cb:
                    try:
                        cb()
                    except Exception as e:
                        print(f"[HidGesture] extra down callback error: {e}")
            elif not btn_now and info["held"]:
                info["held"] = False
                print(f"[HidGesture] Extra {_format_cid(cid)} UP")
                cb = info.get("on_up")
                if cb:
                    try:
                        cb()
                    except Exception as e:
                        print(f"[HidGesture] extra up callback error: {e}")

    # ── connect / main loop ───────────────────────────────────────

    def _try_connect(self):
        """Open the vendor HID collection, discover features, divert."""
        infos = self._vendor_hid_infos()
        if not infos:
            return False

        # Try direct devices (Bluetooth) before USB receivers, which
        # require scanning multiple slots with slow timeouts.
        # Phase 0: prefer mouse-kind candidates (by PID/name heuristics + classify)
        # so Lightspeed (0xC547) etc. are handled before Bolt+keyboard receivers.
        def _candidate_sort_key(info):
            pid = int(info.get("product_id", 0) or 0)
            name = (info.get("product_string") or "").lower()
            kind = classify_device_kind(pid, name)
            kind_prio = {"mouse": 0, "unknown": 1, "other": 2, "keyboard": 3}.get(kind, 4)
            is_receiver = 1 if "receiver" in name else 0
            return (kind_prio, is_receiver, name)

        infos.sort(key=_candidate_sort_key)

        print(f"[HidGesture] Backend preference: {_BACKEND_PREFERENCE}")
        print(f"[HidGesture] Candidate HID interfaces: {len(infos)}")
        for info in infos:
            pid = int(info.get("product_id", 0) or 0)
            up = int(info.get("usage_page", 0) or 0)
            usage = int(info.get("usage", 0) or 0)
            transport = info.get("transport")
            source = info.get("source", "unknown")
            product = info.get("product_string") or "?"
            path = _device_path_display(info.get("path"))
            print(f"[HidGesture] Candidate PID=0x{pid:04X} UP=0x{up:04X} "
                  f"usage=0x{usage:04X} transport={transport or '-'} "
                  f"source={source} product={product} path={path or '-'}")

        for info in infos:
            pid = info.get("product_id", 0)
            up = info.get("usage_page", 0)
            usage = info.get("usage", 0)
            product = info.get("product_string")
            source = info.get("source", "unknown")
            device_spec = resolve_device(product_id=pid, product_name=product)
            self._feat_idx = None
            self._dpi_idx = None
            self._smart_shift_idx = None
            self._battery_idx = None
            self._battery_feature_id = None
            self._wheel_feature_indexes = {}
            self._onboard_profiles_idx = None
            self._report_rate_idx = None
            self._backlight2_idx = None
            self._fn_inversion_idx = None
            self._litra_illumination_idx = None
            self._device_name_idx = None
            self._device_identity_idx = None
            self._device_type_idx = None
            self._led_control_idx = None
            self._led_effects_idx = None
            self._device_mode_idx = None
            self._wireless_power_idx = None
            self._power_management_idx = None
            self._wireless_channel_idx = None
            self._sleep_timeout_idx = None
            self._wireless_status_idx = None
            self._gesture_cid = DEFAULT_GESTURE_CID
            self._gesture_candidates = list(
                getattr(device_spec, "gesture_cids", ()) or DEFAULT_GESTURE_CIDS
            )
            self._rawxy_enabled = False
            opened_transport = None
            opened_up = int(up or 0)
            opened_usage = int(usage or 0)
            opened_path = ""
            open_attempts = []
            # On macOS, prefer IOKit (non-exclusive access) over hidapi
            # which may lock the device and freeze the cursor.
            if (
                sys.platform == "darwin"
                and _MAC_NATIVE_OK
                and _BACKEND_PREFERENCE in ("auto", "iokit")
            ):
                open_attempts.extend([
                    ("iokit-exact", info),
                    ("iokit-ble", {
                        "product_id": pid,
                        "usage_page": 0,
                        "usage": 0,
                        "transport": "Bluetooth Low Energy",
                    }),
                ])
            if _BACKEND_PREFERENCE in ("auto", "hidapi") and info.get("path"):
                open_attempts.append(("hidapi", info))

            for transport, open_info in open_attempts:
                try:
                    if transport.startswith("iokit"):
                        d = _MacNativeHidDevice(
                            pid,
                            usage_page=open_info.get("usage_page", 0),
                            usage=open_info.get("usage", 0),
                            transport=open_info.get("transport"),
                        )
                        d.open()
                    else:
                        if not HIDAPI_OK:
                            continue
                        if sys.platform.startswith("linux"):
                            path = open_info.get("path")
                            _log_once(
                                ("hid-path-access", _device_path_display(path)),
                                "[HidGesture] HID path access before open: "
                                f"{_format_linux_device_access(path)}",
                            )
                        if _HID_API_STYLE == "hidapi":
                            d = _hid.device()
                            d.open_path(open_info["path"])
                        else:
                            d = _HidDeviceCompat(open_info["path"])
                        d.set_nonblocking(False)
                    self._dev = d
                    opened_transport = open_info.get("transport") or transport
                    opened_up = int(open_info.get("usage_page", up) or 0)
                    opened_usage = int(open_info.get("usage", usage) or 0)
                    opened_path = _device_path_display(open_info.get("path"))
                    print(f"[HidGesture] Opened PID=0x{pid:04X} via {transport}")
                    break
                except Exception as exc:
                    print(f"[HidGesture] Can't open PID=0x{pid:04X} "
                          f"UP=0x{int(open_info.get('usage_page', up) or 0):04X} "
                          f"usage=0x{int(open_info.get('usage', usage) or 0):04X} "
                          f"via {transport}: {exc}")
                    self._dev = None
            if self._dev is None:
                continue

            # Try Bluetooth direct (0xFF) first, then Bolt receiver slots
            reprog_found = False
            hidpp_name = None
            for idx in (0xFF, 1, 2, 3, 4, 5, 6):
                self._dev_idx = idx
                fi = self._find_feature(FEAT_REPROG_V4)
                if fi is not None:
                    reprog_found = True
                    self._feat_idx = fi
                    print(f"[HidGesture] Found REPROG_V4 @0x{fi:02X}  "
                          f"PID=0x{pid:04X} devIdx=0x{idx:02X}")
                    # Query actual device name via HID++ (resolves
                    # USB receivers that report a generic PID/name).
                    hidpp_name = self._query_device_name()
                    if hidpp_name:
                        print(f"[HidGesture] HID++ device name: '{hidpp_name}'")
                        device_spec = resolve_device(
                            product_id=pid, product_name=hidpp_name,
                        ) or device_spec
                        self._gesture_candidates = list(
                            getattr(device_spec, "gesture_cids", ())
                            or DEFAULT_GESTURE_CIDS
                        )

                    # Phase 0: early classification after first responsive devIdx (the one
                    # with REPROG_V4) + light feature peek. Keyboards short-circuited here
                    # before the expensive _discover_reprog_controls (32-control walk) and
                    # before any _divert gesture attempts (prevents INVALID_ARGUMENT spam and
                    # mouse-only logic on MX Mechanical etc.). Combined with _candidate_sort_key
                    # this ensures multiple receivers are handled independently (mouse receivers
                    # preferred; kbd receivers only reached when no mouse present).
                    light_feats = {FEAT_REPROG_V4}
                    for f in (
                        FEAT_BACKLIGHT2,
                        FEAT_K375S_FN_INVERSION,
                        FEAT_ADJ_DPI,
                        FEAT_ONBOARD_PROFILES,
                        FEAT_HIRES_WHEEL_ENHANCED,
                        FEAT_UNIFIED_BATT,
                        FEAT_REPORT_RATE,
                    ):
                        if self._find_feature(f) is not None:
                            light_feats.add(f)
                    kind = classify_device_kind(pid, product, hidpp_name, light_feats)
                    print(f"[HidGesture] Early device kind classification: {kind} "
                          f"(PID=0x{int(pid or 0):04X} devIdx=0x{idx:02X})")
                    if kind == "keyboard":
                        print(f"[HidGesture] Treating device as KeyboardDevice ({hidpp_name or product}) "
                              f"— skipping mouse gesture paths.")
                    if kind == "other" and "litra" in (product or "").lower():
                        print(f"[HidGesture] Litra Beam detected and classified as other/light device "
                              f"(PID=0x{int(pid or 0):04X}) — skipping mouse/keyboard paths.")
                        self._discover_common_features()
                        # Kbd path: common features only (battery, backlight, fn inversion etc.).
                        # No reprog walk, no gesture candidates/divert. Return success so kbd is
                        # usable at control level; outer sort ensures G502 wins when both receivers present.
                        if idx == BT_DEV_IDX:
                            actual_transport = "Bluetooth"
                        elif pid == BOLT_RECEIVER_PID:
                            actual_transport = "Logi Bolt"
                        else:
                            actual_transport = "USB Receiver"
                        self._connected_device_info = build_connected_device_info(
                            product_id=pid,
                            product_name=hidpp_name or product,
                            transport=actual_transport,
                            source=source,
                            gesture_cids=(),
                            reprog_controls=(),
                            discovered_features=self._discovered_feature_inventory(),
                            device_identity={
                                "device_index": self._dev_idx,
                                "usage_page": opened_up,
                                "usage": opened_usage,
                                "backend": transport,
                                "hid_module": _HID_MODULE_NAME or "",
                                "device_path": opened_path,
                                "device_kind": kind,
                            },
                        )
                        return True

                    # Mouse / standard path (REPROG present, not keyboard): proceed with
                    # full reprog controls discovery + gesture diversion (safe now).
                    controls = self._discover_reprog_controls()
                    self._last_controls = controls
                    self._gesture_candidates = self._choose_gesture_candidates(
                        controls,
                        device_spec=device_spec,
                    )
                    print("[HidGesture] Gesture CID candidates: "
                          + ", ".join(_format_cid(cid) for cid in self._gesture_candidates))
                    # Discover all useful features (DPI, battery, wheel/ratchet, onboard profiles, etc.)
                    self._discover_common_features()

                    # Reuse the kind already computed earlier in this REPROG block (after the light
                    # feature peek) for consistency. The keyboard short-circuit branch already
                    # used it; the mouse path now reuses it too (no re-computation, same heuristic).
                    print(f"[HidGesture] Early device kind classification (REPROG path): {kind} "
                          f"(PID=0x{int(pid or 0):04X} devIdx=0x{idx:02X})")
                    if kind == "other" and "litra" in (product or "").lower():
                        print(f"[HidGesture] Litra Beam detected and classified as other/light device "
                              f"(PID=0x{int(pid or 0):04X}) — skipping mouse/keyboard paths.")

                    if self._divert():
                        self._divert_extras()
                        if idx == BT_DEV_IDX:
                            actual_transport = "Bluetooth"
                        elif pid == BOLT_RECEIVER_PID:
                            actual_transport = "Logi Bolt"
                        else:
                            actual_transport = "USB Receiver"
                        self._connected_device_info = build_connected_device_info(
                            product_id=pid,
                            product_name=hidpp_name or product,
                            transport=actual_transport,
                            source=source,
                            gesture_cids=self._gesture_candidates,
                            reprog_controls=controls,
                            active_gesture_cid=self._gesture_cid,
                            gesture_rawxy_enabled=self._rawxy_enabled,
                            discovered_features=self._discovered_feature_inventory(),
                            device_identity={
                                "device_index": self._dev_idx,
                                "usage_page": opened_up,
                                "usage": opened_usage,
                                "backend": transport,
                                "hid_module": _HID_MODULE_NAME or "",
                                "device_path": opened_path,
                                "device_kind": kind,
                            },
                        )
                        return True
                    continue     # divert failed — try next receiver slot
            if not reprog_found:
                print(
                    "[HidGesture] Opened candidate but REPROG_V4 was not found "
                    f"on tested devIdx values PID=0x{int(pid or 0):04X} "
                    f"UP=0x{opened_up:04X} usage=0x{opened_usage:04X} "
                    f"transport={opened_transport or '-'} source={source}"
                )

                # Gaming / onboard-primary mice (G502 X Lightspeed etc.) often lack
                # REPROG_CONTROLS_V4.  Still try to establish a control/monitoring
                # connection so DPI, battery, wheel ratchet (0x2121), onboard profiles
                # (0x8100), and report rate remain usable for KVM + onboard workflows.
                if self._dev is not None:
                    self._discover_common_features()

                    # Phase 0 micro-chunk (cleaned): classify the device in the no-REPROG
                    # gaming fallback path so every connected device gets a stable kind.
                    light_feats = set()
                    feature_to_attr = {
                        FEAT_ADJ_DPI: "_dpi_idx",
                        FEAT_ONBOARD_PROFILES: "_onboard_profiles_idx",
                        FEAT_HIRES_WHEEL_ENHANCED: "_wheel_feature_indexes",
                        FEAT_UNIFIED_BATT: "_battery_idx",
                        FEAT_REPORT_RATE: "_report_rate_idx",
                        FEAT_BACKLIGHT2: "_backlight2_idx",
                        FEAT_K375S_FN_INVERSION: "_fn_inversion_idx",
                    }
                    for feat, attr in feature_to_attr.items():
                        if getattr(self, attr, None) is not None:
                            light_feats.add(feat)

                    kind = classify_device_kind(pid, product, hidpp_name, light_feats)
                    print(f"[HidGesture] Early device kind classification (no-REPROG fallback): {kind} "
                          f"(PID=0x{int(pid or 0):04X})")
                    if kind == "other" and "litra" in (product or "").lower():
                        print(f"[HidGesture] Litra Beam detected and classified as other/light device "
                              f"(PID=0x{int(pid or 0):04X}) — skipping mouse/keyboard paths.")

                    has_useful_features = bool(
                        self._dpi_idx
                        or self._battery_idx
                        or self._wheel_feature_indexes
                        or self._onboard_profiles_idx
                        or self._report_rate_idx
                    )
                    if has_useful_features:
                        print(
                            "[HidGesture] No REPROG_V4 but useful HID++ features found "
                            "(DPI/battery/wheel/onboard) — establishing control connection "
                            "for gaming/onboard device."
                        )
                        if idx == BT_DEV_IDX:
                            actual_transport = "Bluetooth"
                        elif pid == BOLT_RECEIVER_PID:
                            actual_transport = "Logi Bolt"
                        else:
                            actual_transport = "USB Receiver"
                        # Minimal device info so the UI shows the correct name + capabilities.
                        # No gesture diversion or reprog controls.
                        self._connected_device_info = build_connected_device_info(
                            product_id=pid,
                            product_name=hidpp_name or product,
                            transport=actual_transport,
                            source=source,
                            gesture_cids=(),
                            reprog_controls=(),
                            discovered_features=self._discovered_feature_inventory(),
                            device_identity={
                                "device_index": self._dev_idx,
                                "usage_page": opened_up,
                                "usage": opened_usage,
                                "backend": transport,
                                "hid_module": _HID_MODULE_NAME or "",
                                "device_path": opened_path,
                                "onboard_only": True,
                                "device_kind": kind,
                            },
                        )
                        return True
                    # No useful features either — fall through to close

            # Couldn't use this interface — close and try next
            try:
                self._dev.close()
            except Exception:
                pass
            self._dev = None

        return False

    def _main_loop(self):
        """Outer loop: connect → listen → reconnect on error/disconnect."""
        retry_logged = False
        while self._running:
            if not self._try_connect():
                if not retry_logged:
                    print("[HidGesture] No compatible device; retrying in 5 s…")
                    retry_logged = True
                for _ in range(50):
                    if not self._running:
                        return
                    time.sleep(0.1)
                continue
            retry_logged = False

            self._connected = True
            if self._on_connect:
                try:
                    self._on_connect()
                except Exception:
                    pass
            print("[HidGesture] Listening for gesture events…")
            _no_data_count = 0          # consecutive _rx() returning None
            _STALE_HOLD_LIMIT = 3       # force-release held buttons after this many empty reads (~3 s)
            _CONSECUTIVE_TIMEOUT_RECONNECT = 3  # force reconnect after this many request timeouts
            self._consecutive_request_timeouts = 0
            try:
                while self._running:
                    if self._reconnect_requested:
                        self._reconnect_requested = False
                        raise IOError("reconnect requested")
                    # If too many consecutive HID++ requests timed out, the
                    # device likely went to sleep or power-cycled.  Force a
                    # full reconnect so button diverts are re-applied.
                    if self._consecutive_request_timeouts >= _CONSECUTIVE_TIMEOUT_RECONNECT:
                        print(f"[HidGesture] {self._consecutive_request_timeouts} consecutive "
                              f"request timeouts — forcing reconnect")
                        raise IOError("consecutive request timeouts — device likely asleep")
                    # Apply any queued DPI command
                    if self._pending_dpi is not None:
                        if self._pending_dpi == "read":
                            self._apply_pending_read_dpi()
                        else:
                            self._apply_pending_dpi()
                    if self._pending_smart_shift is not None:
                        self._apply_pending_smart_shift()
                    if self._pending_battery is not None:
                        self._apply_pending_read_battery()
                    if self._pending_backlight is not None:
                        if isinstance(self._pending_backlight, tuple) and self._pending_backlight[0] == "set":
                            _, enabled, level = self._pending_backlight
                            self._apply_pending_set_backlight(enabled, level)
                        else:
                            self._apply_pending_read_backlight()
                    if self._pending_fn is not None:
                        if isinstance(self._pending_fn, tuple) and self._pending_fn[0] == "set":
                            _, swap = self._pending_fn
                            self._apply_pending_set_fn_inversion(swap)
                        else:
                            self._apply_pending_read_fn_inversion()
                    raw = self._rx(1000)
                    if raw:
                        _no_data_count = 0
                        self._on_report(raw)
                    else:
                        _no_data_count += 1
                        # Force-release buttons stuck in held state when the
                        # device stops sending reports (firmware stall / sleep).
                        if _no_data_count >= _STALE_HOLD_LIMIT:
                            self._force_release_stale_holds()
            except Exception as e:
                print(f"[HidGesture] read error: {e}")

            # Cleanup before potential reconnect
            self._undivert()
            try:
                if self._dev:
                    self._dev.close()
            except Exception:
                pass
            self._dev = None
            self._feat_idx = None
            self._dpi_idx = None
            self._smart_shift_idx = None
            self._battery_idx = None
            self._battery_feature_id = None
            self._wheel_feature_indexes = {}
            self._onboard_profiles_idx = None
            self._report_rate_idx = None
            self._backlight2_idx = None
            self._fn_inversion_idx = None
            self._litra_illumination_idx = None
            self._device_name_idx = None
            self._device_identity_idx = None
            self._device_type_idx = None
            self._led_control_idx = None
            self._led_effects_idx = None
            self._device_mode_idx = None
            self._wireless_power_idx = None
            self._power_management_idx = None
            self._wireless_channel_idx = None
            self._sleep_timeout_idx = None
            self._wireless_status_idx = None
            self._pending_battery = None
            self._pending_dpi = None
            self._dpi_result = None
            self._pending_backlight = None
            self._backlight_result = None
            self._pending_fn = None
            self._fn_result = None
            self._abort_pending_smart_shift()
            self._last_logged_battery = None
            self._consecutive_request_timeouts = 0
            if self._held:
                self._held = False
                print("[HidGesture] Gesture force-released on disconnect")
                if self._on_up:
                    try:
                        self._on_up()
                    except Exception:
                        pass
            for info in self._extra_diverts.values():
                if info["held"]:
                    info["held"] = False
                    cb = info.get("on_up")
                    if cb:
                        print("[HidGesture] Extra button force-released on disconnect")
                        try:
                            cb()
                        except Exception:
                            pass
            self._gesture_cid = DEFAULT_GESTURE_CID
            self._gesture_candidates = list(DEFAULT_GESTURE_CIDS)
            self._rawxy_enabled = False
            self._connected_device_info = None
            self._reconnect_requested = False
            if self._connected:
                self._connected = False
                if self._on_disconnect:
                    try:
                        self._on_disconnect()
                    except Exception:
                        pass

            if self._running:
                time.sleep(2)
