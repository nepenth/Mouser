# Deferred / Out-of-Scope Features

This document records features that are **explicitly deferred** and not planned for the current Mouser roadmap. See also [PROJECT_PLAN.md](PROJECT_PLAN.md) and [EXPANSION_EXECUTION_PLAN.md](EXPANSION_EXECUTION_PLAN.md).

---

## Webcam Features

**Status:** Out of scope (very low priority)

**Source:** [PROJECT_PLAN.md](PROJECT_PLAN.md) — "Webcam-related features (very low priority)."

### Scope statement

Mouser is a **Logitech HID++ companion** focused on mice, keyboards, and Litra lighting. **Webcam control, configuration, or integration is not in scope** for this project.

### Rationale

- Webcams use different APIs (V4L2, UVC, vendor SDKs) and do not share the HID++ feature-handler architecture used throughout Mouser.
- KVM / multi-device workflows in Mouser target pointer, keyboard, and lighting devices — not video capture hardware.
- No webcam stubs exist in `core/`; there is nothing to wire up incrementally.

### If revisited later

A separate effort would be required (new device class, non-HID++ transport, distinct UI surface). Any future work should be tracked as a new initiative, not as an extension of the current FeatureHandler / Engine / Backend stack.

---

## Broader Keyboard Media-Key Diversion (EXPANSION 6.3)

**Status:** Deferred (P3 — optional opt-in)

**Source:** [EXPANSION_EXECUTION_PLAN.md](EXPANSION_EXECUTION_PLAN.md) task 6.3; design doc Phase 2.

### Scope statement

Per-key diversion for Volume/Mute/Search and other media CIDs beyond backlight Up/Down is **not implemented** in the current release. Backlight diversion (TASK-007 / EXPANSION 6.2) is complete and gated by `allow_diversion_backlight`.

### Rationale

- Requires per-CID opt-in UI, expanded config schema, and Linux evdev validation for each key class.
- Risk of accidental global key capture outweighs value before multi-device state model (6.1 XL) is fully mature.

### If revisited later

Add `allow_diversion_media` (and per-CID flags) under `keyboard_middle_path`, extend `_build_extra_diverts`, and ship dedicated UI warnings before enabling defaults.