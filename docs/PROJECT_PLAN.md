# Mouser — Project Plan & Status (as of late 2026)

## Vision

Mouser is evolving from a specialized Logitech mouse remapper into a **local, privacy-first Logitech device companion**.

The goal is to give users excellent **onboard profile** experiences + light, consistent **host-side enhancements** across macOS and Linux (especially KDE Plasma / Wayland) — without ever needing Logitech Options+ or G HUB.

This is particularly valuable for KVM users who own multiple Logitech devices and want behavior to be consistent across machines while still benefiting from useful host-side features (DPI, backlight, FN inversion, selective diversion, battery visibility, etc.).

## Guiding Principles

- **Onboard is Sacred** — Host-side changes must be clearly temporary or opt-in. The device must remain fully functional with zero software.
- **Middle Path for Non-Mice** — Keyboards and other devices get high-value, low-risk host features (backlight, FN, battery, selective key diversion) rather than full remapping.
- **Multi-Receiver Reality** — Properly support users who have both a Lightspeed receiver and a Bolt receiver (or multiple devices).
- **Device-Centric Architecture** — Mice, keyboards, and lights are first-class peers with pluggable feature handlers.
- **No Telemetry, No Cloud, No Account** — Same as the original project.

## Current State (as of this plan)

### Completed / Solid Foundation

**Phase 0 – Multi-Receiver Hygiene + Device Typing**
- Early, reliable device classification (`classify_device_kind`) — mouse vs keyboard vs other.
- Keyboard short-circuit: devices classified as keyboards skip all mouse-specific gesture / RawXY / diversion logic.
- Proper multi-receiver handling (Bolt c548 + Lightspeed c547) with independent discovery and sensible candidate ordering.
- `device_kind` is now present on every connected device (HID++ and evdev paths).
- Graceful “controls-only” fallback when input grabbing is not possible or not desired.

**MX Mechanical Mini Keyboard – Middle Path (the 5 core items)**

1. **Backlight control** (`BACKLIGHT2` 0x1982) — full read + write, host-side only, clearly marked temporary.
2. **FN Inversion** (`K375S_FN_INVERSION` 0x40A3) — read + write support.
3. **Capability flags** — `DeviceCapabilityInventory` now carries `backlight2`, `fn_inversion`, `keyboard_device`, `safe_divert_cids`, etc.
4. **Per-device config skeleton** — `keyboard_middle_path` section in config for future per-device toggles.
5. **Safe diversion foundation** — the two safest backlight CIDs are ready to be selectively diverted behind an explicit opt-in flag.

**General Improvements**
- Many robustness fixes (pending/timeout handling, logging of host-side changes, defensive response parsing).
- All changes reviewed by multiple specialized sub-agents (Senior Code Reviewer, Test Design Reviewer, Acceptance Criteria Validator, Final Plan Validator).

### In Progress / Next

- **Test harness** for the new keyboard middle-path features (improved state-machine and timeout tests are being added).
- **UI layer** for the keyboard (KeyboardPage, per-device toggles for backlight / FN / diversion, clear “host-side only” labeling).
- **Litra Beam** support (illumination control) — next physical device after the keyboard experience is solid.

### Not Yet Started (Future)

- Webcam-related features (very low priority).
- Full per-device policy engine and reconnect replay for host-side keyboard settings.
- Broader UI for multiple device types (sidebar device list, capability-driven pages).

## How to Resume This Work

1. Pull the latest from the repository.
2. Read `docs/PROJECT_PLAN.md` and `docs/LOGITECH_DEVICE_COMPANION_DESIGN.md`.
3. Run the test suite (`python -m unittest discover -s tests`).
4. The current focus areas are:
   - Finishing the test harness for keyboard middle-path features.
   - Building the Keyboard UI (exposing `readBacklight`, `setBacklight`, `readFnInversion`, etc. through the backend and creating a basic KeyboardPage).
   - Beginning Litra Beam illumination support.

## Key Files

- `docs/LOGITECH_DEVICE_COMPANION_DESIGN.md` — Detailed architecture and phased plan.
- `docs/PROJECT_PLAN.md` — This living status document.
- `core/hid_gesture.py` — Core HID++ logic, classification, keyboard feature handlers.
- `core/logi_devices.py` — Device typing, capability inventory.
- `ui/backend.py` — Thin exposure of new keyboard methods.
- `tests/test_hid_gesture.py` — Growing test coverage for the new paths.

## Contributing / Working Style

We work in **small, reviewable micro-chunks** and use specialized sub-agents for:
- Code review (design fidelity, “onboard is sacred”, middle-path discipline)
- Validation against acceptance criteria
- Test design review

This allows steady progress with high quality and minimal context switching.

---

*Last updated: during active autonomous development session focused on keyboard middle-path + multi-device generalization.*