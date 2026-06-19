"""
HID++ feature IDs, protocol constants, and small parsing/format helpers.

Extracted from hid_gesture.py (Phase 5.2 Pass 1) so the listener module can
shrink while keeping a single source of truth for Logitech HID++ symbols.
"""

from __future__ import annotations

# ── Vendor / protocol ─────────────────────────────────────────────
LOGI_VID = 0x046D

SHORT_ID = 0x10        # HID++ short report (7 bytes total)
LONG_ID = 0x11         # HID++ long  report (20 bytes total)
SHORT_LEN = 7
LONG_LEN = 20

BT_DEV_IDX = 0xFF        # device-index for direct Bluetooth
# Known Logi Bolt receiver PID.
# Source: https://github.com/pwr-Solaar/Solaar/blob/master/lib/logitech_receiver/base_usb.py
BOLT_RECEIVER_PID = 0xC548

# ── HID++ feature IDs ─────────────────────────────────────────────
FEAT_IROOT = 0x0000
FEAT_REPROG_V4 = 0x1B04      # Reprogrammable Controls V4
FEAT_ADJ_DPI = 0x2201      # Adjustable DPI
FEAT_SMART_SHIFT = 0x2110  # Smart Shift basic
FEAT_SMART_SHIFT_ENHANCED = 0x2111  # Smart Shift Enhanced (MX Master 3/3S, MX Master 4)
FEAT_HIRES_WHEEL = 0x2120
FEAT_HIRES_WHEEL_ENHANCED = 0x2121
FEAT_LOWRES_WHEEL = 0x2130
FEAT_THUMB_WHEEL = 0x2150
FEAT_UNIFIED_BATT = 0x1004      # Unified Battery (preferred)
FEAT_ONBOARD_PROFILES = 0x8100    # Gaming mice (G502 X etc.) - onboard memory + profiles
FEAT_REPORT_RATE = 0x8060      # Report rate control (gaming mice)

# Keyboard / general device features (MX Mechanical Mini, etc.)
FEAT_BACKLIGHT2 = 0x1982   # Backlight control (V2 on MX Mechanical Mini)
FEAT_K375S_FN_INVERSION = 0x40A3   # FN / Fx swap (common on MX Mechanical family)
FEAT_DEVICE_NAME = 0x0005      # Device Name & Type
# SOURCE: unverified — _find_feature probe only; is_supported False when absent
FEAT_DEVICE_IDENTITY = 0x0003     # Device Serial Number / Hardware Version / Identity (probe candidate)
# SOURCE: unverified — _find_feature probe only; is_supported False when absent
FEAT_DEVICE_TYPE = 0x0002     # Device Type / Product Type (probe candidate)
FEAT_BATTERY_STATUS = 0x1000      # Battery Status (fallback)

# Litra Beam (and similar Logitech lights) illumination control
# HID++ ILLUMINATION (Solaar SupportedFeature.ILLUMINATION); not PRESENTER_CONTROL 0x1A00.
FEAT_LITRA_ILLUMINATION = 0x1990
FEAT_LITRA_ILLUMINATION_LEGACY = 0x1A00  # runtime fallback only (was incorrect placeholder)
# SOURCE: Solaar SupportedFeature.LED_CONTROL — https://github.com/pwr-Solaar/Solaar/blob/master/lib/logitech_receiver/hidpp20_constants.py
FEAT_LED_CONTROL = 0x1300  # LED control (on/off + brightness)
# SOURCE: Solaar SupportedFeature.COLOR_LED_EFFECTS — https://github.com/pwr-Solaar/Solaar/blob/master/lib/logitech_receiver/hidpp20_constants.py
FEAT_LED_EFFECTS = 0x8070  # LED effects (patterns/modes beyond basic on/off + brightness)
# SOURCE: Solaar SupportedFeature.DEVICE_MODE — https://github.com/pwr-Solaar/Solaar/blob/master/lib/logitech_receiver/hidpp20_constants.py
FEAT_DEVICE_MODE = 0x1B30  # Device Mode / Wireless Mode
# SOURCE: Solaar SupportedFeature.WIRELESS_SIGNAL_STRENGTH (closest RF/link match) — https://github.com/pwr-Solaar/Solaar/blob/master/lib/logitech_receiver/hidpp20_constants.py
FEAT_WIRELESS_POWER = 0x0080  # Wireless Power / RF Power Management (signal strength proxy)
# SOURCE: unverified — _find_feature probe only; is_supported False when absent
FEAT_POWER_MANAGEMENT = 0x1C01  # Power Management (beyond Sleep Timeout / Wireless Power; probe candidate)
FEAT_REMAINING_PAIRING = 0x1DF0  # Remaining Pairing slots (standard HID++ feature)
# SOURCE: Solaar SupportedFeature.FORCE_SENSING_BUTTON — https://github.com/pwr-Solaar/Solaar/blob/master/lib/logitech_receiver/hidpp20_constants.py
FEAT_FORCE_SENSING_BUTTON = 0x19C0  # Force Sensing Button (pressure-sensitive buttons)
# SOURCE: unverified — _find_feature probe only; is_supported False when absent
FEAT_WIRELESS_CHANNEL = 0x1D00  # Wireless Channel / RF Channel (probe candidate)
# SOURCE: Solaar SupportedFeature.WIRELESS_DEVICE_STATUS — https://github.com/pwr-Solaar/Solaar/blob/master/lib/logitech_receiver/hidpp20_constants.py
FEAT_WIRELESS_STATUS = 0x1D4B  # Wireless Status (link quality / RSSI)
# SOURCE: unverified — _find_feature probe only; is_supported False when absent
FEAT_SLEEP_TIMEOUT = 0x1E00  # Sleep Timeout / Power Save Timeout (probe candidate)

# ── Gesture / software IDs ────────────────────────────────────────
DEFAULT_GESTURE_CIDS = (0x00C3, 0x00D7)
DEFAULT_GESTURE_CID = DEFAULT_GESTURE_CIDS[0]

MY_SW = 0x0A        # arbitrary software-id used in our requests

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


# ── HID++ parsing / formatting helpers ────────────────────────────

def parse_hidpp_report(raw):
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
    dev = raw[off]
    feat = raw[off + 1]
    fsw = raw[off + 2]
    func = (fsw >> 4) & 0x0F
    sw = fsw & 0x0F
    params = raw[off + 3:]
    return dev, feat, func, sw, params


def format_hidpp_bytes(data):
    if not data:
        return "-"
    return " ".join(f"{int(b) & 0xFF:02X}" for b in data)


def format_flag_bits(value, bit_names):
    names = [name for bit, name in bit_names if value & bit]
    return ",".join(names) if names else "none"


def format_control_id(cid):
    name = KNOWN_CID_NAMES.get(cid)
    return f"0x{cid:04X} ({name})" if name else f"0x{cid:04X}"