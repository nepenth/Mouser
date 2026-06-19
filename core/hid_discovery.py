"""
Logitech HID device discovery helpers.

Extracted from hid_gesture.py (Phase 5.2 Pass 1): classification, candidate
sorting, and Linux hidraw/sysfs diagnostics.  build_connected_device_info and
the device catalog remain in core.logi_devices.
"""

from __future__ import annotations

import os
import stat
import sys

from core.hid_features import (
    FEAT_ADJ_DPI,
    FEAT_BACKLIGHT2,
    FEAT_HIRES_WHEEL_ENHANCED,
    FEAT_ONBOARD_PROFILES,
    LOGI_VID,
)
from core.logi_devices import resolve_device


def device_path_display(path):
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


def format_linux_device_access(path):
    if isinstance(path, memoryview):
        path = bytes(path)
    display = device_path_display(path)
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


def summarize_hid_infos(infos, limit=8):
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


def linux_logitech_hidraw_nodes(base="/sys/class/hidraw"):
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
    has_dpi = FEAT_ADJ_DPI in feats or 0x2201 in feats
    has_onboard = FEAT_ONBOARD_PROFILES in feats or 0x8100 in feats
    has_hires = FEAT_HIRES_WHEEL_ENHANCED in feats or 0x2121 in feats
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


def sort_hid_candidates(infos):
    """Sort HID interface candidates in-place: mice first, then receivers."""

    def _candidate_sort_key(info):
        pid = int(info.get("product_id", 0) or 0)
        name = (info.get("product_string") or "").lower()
        kind = classify_device_kind(pid, name)
        kind_prio = {"mouse": 0, "unknown": 1, "other": 2, "keyboard": 3}.get(kind, 4)
        is_receiver = 1 if "receiver" in name else 0
        return (kind_prio, is_receiver, name)

    infos.sort(key=_candidate_sort_key)


def enumerate_vendor_hid_infos(
    *,
    hidapi_ok: bool,
    backend_preference: str,
    hid_enumerate,
    hid_module_name: str | None,
    log_once,
    resolve_device_fn=resolve_device,
    platform: str | None = None,
    mac_native_ok: bool = False,
    mac_enumerate_infos=None,
):
    """Return candidate Logitech HID interfaces from hidapi and macOS IOKit."""
    platform = sys.platform if platform is None else platform
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

    if hidapi_ok and backend_preference in ("auto", "hidapi"):
        try:
            raw_infos = list(hid_enumerate(LOGI_VID, 0))
            if not raw_infos:
                log_once(
                    f"hidapi-empty-{hid_module_name}",
                    "[HidGesture] "
                    f"{hid_module_name or 'hidapi'} enumerate(0x{LOGI_VID:04X}) "
                    "returned no Logitech HID interfaces"
                )
                linux_nodes = linux_logitech_hidraw_nodes()
                if linux_nodes:
                    log_once(
                        "linux-hidraw-logitech-present",
                        "[HidGesture] Linux sysfs sees Logitech hidraw nodes: "
                        f"{'; '.join(linux_nodes[:8])}. If hidapi still sees "
                        "none, check hidraw backend packaging and /dev/hidraw "
                        "permissions."
                    )
                elif platform.startswith("linux"):
                    log_once(
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
                if resolve_device_fn(product_id=pid, product_name=product):
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
                log_once(
                    f"hidapi-filtered-{hid_module_name}",
                    "[HidGesture] Filtered Logitech HID interfaces: "
                    f"{summarize_hid_infos(raw_infos)}"
                )
        except Exception as exc:
            print(f"[HidGesture] hidapi enumerate error: {exc}")

    if (
        platform == "darwin"
        and mac_native_ok
        and backend_preference in ("auto", "iokit")
        and mac_enumerate_infos is not None
    ):
        for info in mac_enumerate_infos():
            add_info(info)

    return out