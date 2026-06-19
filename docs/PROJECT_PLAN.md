# Mouser — Project Plan & Status (June 2026)

## Vision

Mouser is evolving from a specialized Logitech mouse remapper into a **local, privacy-first Logitech device companion**.

The goal is excellent **onboard profile** experiences plus light, consistent **host-side enhancements** across macOS and Linux (especially KDE Plasma / Wayland) — without Logitech Options+ or G HUB.

This is particularly valuable for KVM users with multiple Logitech devices who want consistent behavior across machines while still benefiting from useful host-side features (DPI, backlight, FN inversion, selective diversion, battery visibility, Litra illumination, etc.).

## Guiding Principles

- **Onboard is Sacred** — Host-side changes are clearly temporary or opt-in. Devices remain fully functional with zero software.
- **Middle Path for Non-Mice** — Keyboards get high-value, low-risk host features (backlight, FN, battery, selective key diversion) rather than full remapping.
- **Multi-Receiver Reality** — Support users with both Lightspeed and Bolt receivers (or multiple devices).
- **Device-Centric Architecture** — Mice, keyboards, and lights are first-class peers with pluggable FeatureHandlers.
- **No Telemetry, No Cloud, No Account** — Same as the original project.

## Current State

### Solid Foundation (Phases 0–2 + Task A complete)

**Expansion execution (Phases 0–2)** — upstream merge, G502 support, test regressions fixed, full suite green.

**Phase 0 – Multi-Receiver Hygiene + Device Typing**
- Reliable `classify_device_kind` (mouse / keyboard / other / Litra).
- Keyboard short-circuit: keyboards skip mouse gesture / RawXY / diversion logic.
- Multi-receiver handling (Bolt c548 + Lightspeed c547) with candidate ordering and structured discovery logging.
- `device_kind` on every connected device (HID++ and evdev paths).
- Controls-only fallback when input grabbing is not possible.

**FeatureHandler architecture (TASK-009)**
- **20 FeatureHandlers** in `core/devices/` (battery, DPI, SmartShift, report rate, onboard profiles, device name/identity/type, LED, wireless, power management, Litra illumination, backlight, FN inversion, force sensing, remaining pairing, etc.).
- Engine lazy attachment + `_delegate_or_fallback`; Backend exposes **100% Engine HID++ API parity** (Task A complete).
- Handler base hierarchy: `RecommendedThinHandler` / `UltraThinHandler` with documented patterns.

**MX Mechanical Mini – Middle Path (delivered)**
1. **Backlight** (`BACKLIGHT2` 0x1982) — read + write via `BacklightHandler`.
2. **FN Inversion** (`K375S_FN_INVERSION` 0x40A3) — read + write via `FnInversionHandler`.
3. **Per-device config** — `keyboard_middle_path` flags (`allow_host_backlight`, `allow_fn_inversion`, `allow_diversion_backlight`).
4. **Host-side replay on reconnect** — backlight + FN values replay when per-device flags allow.
5. **Safe selective diversion** — backlight Up/Down CIDs gated behind explicit opt-in; mappable as diverted keys.

**Litra Beam**
- Classification, illumination read/write, `hasLitraIlluminationSupported` capability property.
- Dedicated **LitraPage** + footer quick-access controls (host-side only labeling).

**UI surfaces**
- **KeyboardPage** — backlight, FN inversion, per-device permission toggles, device status, diversion opt-in.
- **LitraPage** — on/off + brightness with refresh/error handling.
- Context-aware footer cards hidden on dedicated pages.

**Quality & testing**
- **658 tests** passing (`python -m unittest discover -s tests`; 10 skipped).
- Keyboard middle-path harness: pending/apply state machine, timeouts, classification, reconnect replay, handler delegation.
- `tools/linux_smoke_test.py` + `docs/LINUX_TESTING.md` for no-hardware Linux validation.
- `docs/ARCHITECTURE_GUIDE.md` for adding handlers, Backend slots, and tests.

**Upstream integration**
- G502 family layouts, screenshot actions, a11y/tray improvements, CI alignment.

### In Progress

- **Task 7.3** — Living documentation sync (this plan + execution dashboard).
- **Phase 4.6** — Multi-device UI (sidebar device list, `connectedDevices`, per-device page routing).
- **Phase 5–6** — Architecture decomposition (`hid_gesture.py` split), multi-device state model, Linux evdev diversion validation.

### Not Yet Started / Deferred

- Webcam features — explicitly deferred (`docs/DEFERRED.md`).
- Full per-device KVM preset UI (config skeleton exists).
- Broader keyboard media-key diversion (opt-in, Phase 2 design).
- `LogitechDevice` subclasses (Mouse/Keyboard/Other factory).

## How to Resume This Work

1. Pull latest; read `docs/PROJECT_PLAN.md`, `docs/EXPANSION_EXECUTION_PLAN.md`, `docs/ARCHITECTURE_GUIDE.md`.
2. Run `python -m unittest discover -s tests` (expect 658 OK).
3. On Linux: `python tools/linux_smoke_test.py` for quick smoke validation.
4. Current focus: multi-device UI (4.6), then high-risk state-model refactor (6.1).

## Key Files

| Area | Path |
|------|------|
| Design | `docs/LOGITECH_DEVICE_COMPANION_DESIGN.md` |
| Task board | `docs/TASKS.md` |
| Execution plan | `docs/EXPANSION_EXECUTION_PLAN.md` |
| Handlers | `core/devices/*_handler.py` |
| HID++ core | `core/hid_gesture.py`, `core/engine.py` |
| Backend API | `ui/backend.py` |
| Keyboard / Litra UI | `ui/qml/KeyboardPage.qml`, `ui/qml/LitraPage.qml` |
| Tests | `tests/test_hid_gesture.py`, `tests/test_backend.py` |
| Linux harness | `tools/linux_smoke_test.py`, `docs/LINUX_TESTING.md` |

## Contributing / Working Style

Small, reviewable micro-chunks with specialized review passes (design fidelity, acceptance criteria, test design). Steady progress with high quality and minimal context switching.

---

*Last updated: 2026-06-19 — expansion through Tasks 7.1–7.2; 658 tests green.*