"""Shared multi-device state helpers (Engine + Backend)."""

from __future__ import annotations

from core.logi_devices import iter_known_devices, resolve_device


def display_name_for_device_key(key: str) -> str:
    for spec in iter_known_devices():
        if spec.key == key:
            return spec.display_name
    try:
        pid = int(key, 16)
    except (TypeError, ValueError):
        return str(key).replace("_", " ").title()
    spec = resolve_device(product_id=pid)
    if spec:
        return spec.display_name
    return f"Logitech PID 0x{pid:04X}"


def device_kind_from_connected(device) -> str:
    if device is None:
        return "other"
    inventory = getattr(device, "capability_inventory", None)
    if inventory is not None:
        identity = dict(getattr(inventory, "device_identity", ()) or ())
        kind = identity.get("device_kind", "")
        if kind == "unknown":
            kind = "other"
        if kind in ("mouse", "keyboard", "other"):
            return kind
        if getattr(inventory, "keyboard_device", False):
            return "keyboard"
    name = (getattr(device, "display_name", "") or "").lower()
    if any(token in name for token in ("g502", "mx master", "mx anywhere", "mx vertical", "mouse")):
        return "mouse"
    if any(token in name for token in ("mechanical", "keyboard", "mx keys")):
        return "keyboard"
    if "litra" in name:
        return "other"
    return "other"


def connected_device_key(device) -> str:
    if device is None:
        return ""
    device_key = getattr(device, "key", "") or ""
    if device_key:
        return device_key
    product_id = getattr(device, "product_id", None)
    if product_id not in (None, ""):
        return str(product_id)
    return ""


def build_all_devices_list(
    cfg,
    connected_device=None,
    *,
    mouse_connected: bool = False,
    battery_level: int = -1,
) -> list[dict]:
    """Build device info dicts for config entries plus the connected device."""
    entries_by_key: dict[str, dict] = {}
    for key in cfg.get("devices", {}):
        if not key:
            continue
        entries_by_key[key] = {
            "key": key,
            "displayName": display_name_for_device_key(key),
            "deviceKind": "other",
            "batteryLevel": -1,
            "connected": False,
        }

    device_key = connected_device_key(connected_device)
    if device_key:
        entries_by_key[device_key] = {
            "key": device_key,
            "displayName": getattr(connected_device, "display_name", "") or device_key,
            "deviceKind": device_kind_from_connected(connected_device),
            "batteryLevel": battery_level,
            "connected": bool(mouse_connected),
        }

    return sorted(
        entries_by_key.values(),
        key=lambda entry: (not entry["connected"], entry["displayName"].lower()),
    )


def active_mouse_device_from_connected(connected_device):
    """Return the connected device when it is a mouse; otherwise None."""
    if connected_device is None:
        return None
    if device_kind_from_connected(connected_device) == "mouse":
        return connected_device
    return None