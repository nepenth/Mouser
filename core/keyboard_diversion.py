"""Per-device keyboard key diversion catalog (EXPANSION 6.3 / design Phase 2).

Maps opt-in config flags to HID++ control IDs (CIDs) and Mouser button event names.
MX Mechanical Mini CIDs are verified against Solaar B367 dumps; media keys use
Solaar CONTROL task names with CID candidate fallbacks resolved at connect time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


# Product IDs that support the MX Mechanical Mini diversion table.
MX_MECHANICAL_MINI_PIDS = frozenset({0xB367, 0xB369, 0xB36B})

KEYBOARD_MIDDLE_PATH_DIVERSION_KEYS = frozenset({
    "allow_diversion_backlight",
    "allow_diversion_volume",
    "allow_diversion_mute",
    "allow_diversion_search",
})


@dataclass(frozen=True)
class KeyboardDivertSpec:
    """One divertable keyboard control."""

    config_flag: str
    cid_candidates: tuple[int, ...]
    event_stem: str  # e.g. keyboard_volume_up -> keyboard_volume_up_down/_up
    label: str
    # Solaar REPROG task IDs (getCidInfo bytes 2-3) used to match at runtime when present.
    task_candidates: tuple[int, ...] = ()

    @property
    def down_event(self) -> str:
        return f"{self.event_stem}_down"

    @property
    def up_event(self) -> str:
        return f"{self.event_stem}_up"


# MX Mechanical Mini: backlight 0x00C5/0x00C6 (Mouser-verified); media/search from
# Solaar CONTROL + B367 REPROG dump task ordering.
MX_MECHANICAL_MINI_DIVERT_SPECS: tuple[KeyboardDivertSpec, ...] = (
    KeyboardDivertSpec(
        "allow_diversion_backlight",
        (0x00C5,),
        "keyboard_backlight_up",
        "Backlight Up",
    ),
    KeyboardDivertSpec(
        "allow_diversion_backlight",
        (0x00C6,),
        "keyboard_backlight_down",
        "Backlight Down",
    ),
    KeyboardDivertSpec(
        "allow_diversion_volume",
        (0x00C9, 0x00E9),
        "keyboard_volume_up",
        "Volume Up",
        task_candidates=(0x00E9, 0x0001),
    ),
    KeyboardDivertSpec(
        "allow_diversion_volume",
        (0x00C8, 0x00E8),
        "keyboard_volume_down",
        "Volume Down",
        task_candidates=(0x00E8, 0x0002),
    ),
    KeyboardDivertSpec(
        "allow_diversion_mute",
        (0x00C7, 0x00E7, 0x0003),
        "keyboard_mute",
        "Mute",
        task_candidates=(0x00E7, 0x0003),
    ),
    KeyboardDivertSpec(
        "allow_diversion_search",
        (0x00D4, 0x003E),
        "keyboard_search",
        "Search",
        task_candidates=(0x00D4, 0x003E),
    ),
)

# Friendly profile / action-selector aliases (007.5 pattern for backlight).
DIVERT_EVENT_ALIASES: dict[str, str] = {
    "backlight_up": "keyboard_backlight_up",
    "backlight_down": "keyboard_backlight_down",
    "volume_up": "keyboard_volume_up",
    "volume_down": "keyboard_volume_down",
    "mute": "keyboard_mute",
    "search": "keyboard_search",
}


def is_mx_mechanical_mini_device(*, name: str = "", product_id: int = 0) -> bool:
    if product_id in MX_MECHANICAL_MINI_PIDS:
        return True
    lowered = (name or "").lower()
    return "mx mechanical mini" in lowered


def resolve_divert_cid(
    spec: KeyboardDivertSpec,
    *,
    reprog_cids: frozenset[int] | set[int] | None = None,
    task_to_cid: dict[int, int] | None = None,
) -> int | None:
    """Pick the best CID for a divert spec using runtime REPROG data when available."""
    task_to_cid = task_to_cid or {}
    reprog = reprog_cids or set()

    for task_id in spec.task_candidates:
        cid = task_to_cid.get(task_id)
        if cid is not None and (not reprog or cid in reprog):
            return cid

    for cid in spec.cid_candidates:
        if not reprog or cid in reprog:
            return cid

    return None


def build_keyboard_extra_diverts(
    *,
    cfg,
    device,
    dispatch_factory: Callable[[str], dict[str, Callable]],
    reprog_cids: frozenset[int] | set[int] | None = None,
    task_to_cid: dict[int, int] | None = None,
) -> dict[int, dict]:
    """Build extra_diverts dict for BaseMouseHook from per-device opt-in flags."""
    from core.config import get_keyboard_middle_path_settings

    extra: dict[int, dict] = {}
    if not device or not cfg:
        return extra

    name = getattr(device, "name", "") or ""
    pid = int(getattr(device, "product_id", 0) or 0)
    if not is_mx_mechanical_mini_device(name=name, product_id=pid):
        return extra

    device_key = getattr(device, "key", None) or str(pid)
    kmp = get_keyboard_middle_path_settings(cfg, device_key)

    for spec in MX_MECHANICAL_MINI_DIVERT_SPECS:
        if not kmp.get(spec.config_flag, False):
            continue
        cid = resolve_divert_cid(spec, reprog_cids=reprog_cids, task_to_cid=task_to_cid)
        if cid is None or cid in extra:
            continue
        handlers = dispatch_factory(spec.event_stem)
        extra[cid] = {
            "on_down": handlers["on_down"],
            "on_up": handlers["on_up"],
            "label": spec.label,
        }
        print(
            f"[MouseHook] Enabling opt-in {spec.label} diversion "
            f"(CID=0x{cid:04X}, flag {spec.config_flag}=True, device={device_key})"
        )

    return extra


def resolve_diverted_keyboard_action(mappings: dict, event: str) -> str:
    """Map a diverted keyboard event string to a profile action id."""
    action_id = mappings.get(event, "none")
    if action_id != "none":
        return action_id

    from core.config import BUTTON_TO_EVENTS

    for btn_key, events in BUTTON_TO_EVENTS.items():
        if event in events:
            action_id = mappings.get(btn_key, "none")
            if action_id != "none":
                return action_id

    for alias, stem in DIVERT_EVENT_ALIASES.items():
        if event.startswith(f"{stem}_"):
            action_id = mappings.get(alias, "none")
            if action_id != "none":
                return action_id

    return "none"