# Mouser — Local Logitech Device Companion

<p align="center">
  <img src="images/logo_icon.png" width="128" alt="Mouser logo" />
</p>

**Mouser** is a lightweight, fully local companion application for Logitech HID++ devices.

It began as a focused mouse remapper for the MX Master and MX Anywhere families. It is now evolving into a broader **local Logitech device companion** with a strong emphasis on:

- Respecting **onboard profiles** as the source of truth (especially valuable for KVM users)
- Adding light, safe, **host-side enhancements** only where they provide clear value
- Supporting multiple device types (mice, keyboards, lights, etc.) through a device-centric architecture

**No telemetry. No cloud. No Logitech account required.**

---

## Current Development Focus

We are actively expanding Mouser to support the devices in one primary user's KVM setup:

- **G502 X Lightspeed** — Mouse with strong onboard profile + host enhancement support
- **MX Mechanical Mini** — Keyboard with "middle path" support (backlight, FN inversion, selective safe diversion)
- **Litra Beam** — Lightbar (planned)

The long-term vision is a clean, maintainable platform for local control of multiple Logitech device categories without ever needing Logitech Options+ or G HUB.

**For the latest status, detailed plan, and active task list, see:**
- [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md)
- [docs/TASKS.md](docs/TASKS.md) (actionable tasks with requirements & acceptance criteria)
- [docs/LOGITECH_DEVICE_COMPANION_DESIGN.md](docs/LOGITECH_DEVICE_COMPANION_DESIGN.md) (architecture)

---

## Download & Run

> **No install required.** Just download, extract, and double-click.

Downloads are available on the [latest release page](https://github.com/TomBadash/Mouser/releases/latest).

See the original installation instructions in the [legacy documentation](#legacy-mouse-remapper-documentation) section below if you are primarily using Mouser as a mouse remapper.

---

## Philosophy & Design Principles

- **Onboard is Sacred** — Host-side changes must be clearly temporary or opt-in. The device must remain fully functional with zero software.
- **Middle Path for Non-Mice** — Keyboards and lights get high-value, low-risk features rather than attempting full remapping.
- **Multi-Receiver Reality** — We properly support users running both Lightspeed and Bolt receivers.
- **Device-Centric** — Different device types (mouse, keyboard, light) are first-class citizens.
- **Local First** — Everything runs locally. No accounts, no cloud, no telemetry.

---

## Completed Work Log

This is the authoritative running log of completed and **accepted** work. Tasks are only recorded here after they have passed review and acceptance criteria validation by specialized sub-agents (acting as expert reviewers).

### Major Completed Work

**Phase 0 – Foundation (Multi-Device Hygiene)**
- Multi-receiver support and early device classification (mouse vs keyboard)
- Keyboard short-circuit logic (keyboards skip mouse gesture paths)
- Consistent `device_kind` across HID++ and evdev paths
- Graceful controls-only fallback behavior

**MX Mechanical Mini – Middle Path Backend (Core 5 Items)**
- Backlight control via BACKLIGHT2 (read + write, host-side only)
- FN inversion support (read + write)
- Capability flags in `DeviceCapabilityInventory`
- Per-device middle-path config skeleton
- Safe diversion foundation for backlight keys

**Quality & Process Improvements**
- Multiple rounds of sub-agent code review and acceptance criteria validation
- Significant improvements to pending/timeout handling, logging of host-side changes, and response parsing robustness
- TASK-001 (P0) accepted and committed: Fix Backend Exposure Bug for Keyboard Methods — corrected the four readBacklight/setBacklight/readFnInversion/setFnInversion delegates in ui/backend.py from erroneous direct `self._engine._hid_gesture` access to the proper `engine.hook._hid_gesture` path (with safe guards). Passed internal code review (design fidelity, consistency, no regressions) and strict Acceptance Criteria validation.
- TASK-002 (P0) accepted and committed: Complete High-Quality Test Harness for Keyboard Middle-Path Features — added/expanded state-machine tests for pending/apply + timeout behavior on BACKLIGHT2 and FN inversion, fixed classification heuristic priority (mouse features now correctly win), removed broken placeholder test + added scoped TODO. 11/11 MXMechanicalMiniMiddlePathTests green; no mouse regressions. Passed Code Review + strict Acceptance Criteria validation (Project Manager acting as reviewers).
- TASK-004 micro-chunk 004.1 accepted and committed: Added stable public API (`read_backlight`, `set_backlight`, `read_fn_inversion`, `set_fn_inversion`) on the `Engine` class with defensive delegation and explicit "host-side, temporary" documentation. Cleaned up `ui/backend.py` to delegate through the new Engine surface instead of private hook access. Passed Code Review + AC validation.
- TASK-004 micro-chunk 004.2 accepted and committed: Added `has_backlight_control()` / `has_fn_inversion_control()` on Engine plus `keyboardBacklightSupported` / `keyboardFnInversionSupported` read-only properties on Backend (wired to `hidFeaturesReadyChanged`). Clean capability surface for future Keyboard UI. Passed Code Review + AC validation.
- TASK-005 micro-chunk 005.1 accepted and committed: First real user-facing keyboard middle-path UI. Added `KeyboardControls.qml` (conditional card with backlight toggle+slider and FN inversion toggle + prominent “TEMPORARY — host-side only” warning). Integrated as footer below existing mouse pages in Main.qml using the new capability flags. Passed Code Review + AC validation.
- TASK-005 micro-chunk 005.2 accepted and committed: Robustness & polish pass on the new keyboard controls card. Added refreshing state + disabled controls during refresh, non-intrusive auto-clearing error feedback for failed set calls, 350 ms debounce on brightness slider, Connections for capability changes, and stronger null handling. All confined to KeyboardControls.qml. Passed Code Review + AC validation.
- TASK-005 micro-chunk 005.3 accepted and committed: Added dedicated `KeyboardPage.qml` (hosts the existing controls + header + temporary warning) and wired a third "Keyboard" sidebar navigation entry (page 2) into Main.qml. First structural step toward a proper keyboard section. Passed Code Review + AC validation.
- TASK-005 micro-chunk 005.4 accepted and committed: Added basic device status block to KeyboardPage (device name, connection type, battery level when available). Status only appears for supported middle-path keyboards. Reused existing backend properties. Passed Code Review + AC validation.
- TASK-005 micro-chunk 005.5 accepted and committed: Made the quick-access KeyboardControls footer context-aware — it is now hidden when the user is on the dedicated Keyboard page (reduces duplication). Footer behavior unchanged on Mouse/Scroll pages. Passed Code Review + AC validation.
- TASK-006 micro-chunk 006.1 accepted and committed: Added per-device `devices.<key>.keyboard_middle_path` structure in config + helper functions (`get_keyboard_middle_path_settings`, `set_keyboard_middle_path_setting`). Safe defaults favoring host enhancements. No behavior change yet. Passed Code Review + AC validation.
- TASK-006 micro-chunk 006.2 accepted and committed: Added guards in `Engine.set_backlight()` and `set_fn_inversion()` that respect the new per-device `allow_host_*` flags. Blocked calls are logged and refused. First behavioral enforcement of per-device policy. Passed Code Review + AC validation.
- TASK-006 micro-chunk 006.3 accepted and committed: Exposed the two per-device settings via thin Backend methods and added "Host Control Permissions" toggles on KeyboardPage.qml. First complete end-to-end per-device middle-path feature (config + enforcement + UI control). Passed Code Review + AC validation.
- TASK-006 micro-chunk 006.4 accepted and committed: Made the permission toggles reactive — they now automatically update when the connected keyboard changes while the KeyboardPage is open (KVM usability improvement). Passed Code Review + AC validation.
- TASK-007 micro-chunk 007.1 accepted and committed: Started safe selective key diversion work. Extended per-device config with allow_diversion_backlight (default false) and added the corresponding opt-in toggle on KeyboardPage.qml (with clear warning text). No actual diversion logic yet. Passed Code Review + AC validation.
- TASK-007 micro-chunk 007.2 accepted and committed: First real gated diversion wiring. Extended the hook to conditionally register the two safest MX Mechanical Mini backlight CIDs (0x00C5/0x00C6) only when allow_diversion_backlight is explicitly true for that device. When the flag is false (default), the keys are untouched on the onboard profile. Clear logging + placeholder handlers. Passed Code Review + AC validation.
- TASK-007 micro-chunk 007.3 accepted and committed: Implemented real dispatch for the diverted backlight keys. When opted in, Backlight Up/Down presses now generate visible host events (keyboard_backlight_up_down/up, keyboard_backlight_down_down/up) via the existing gesture callback path. Events are visible to the mapping/debug system. Passed Code Review + AC validation.
- TASK-007 micro-chunk 007.4 accepted and committed: Made the four diverted backlight key events first-class mappable buttons (registered in BUTTON_NAMES / BUTTON_TO_EVENTS with clear "(diverted)" labels). Extended Engine gesture handling to route them to active profile mappings and execute assigned actions. Users can now assign normal Mouser actions to the opted-in diverted keys through the existing action system. Passed Code Review + AC validation.
- TASK-007 micro-chunk 007.5 accepted and committed: Small polish pass — introduced cleaner canonical names (backlight_up / backlight_down) with friendly “(diverted)” labels, dual-name mapping support in the Engine, and improved debug logging for the diverted events. Makes the first complete diversion feature feel first-class and usable. Passed Code Review + AC validation.
- TASK-008 micro-chunk 008.1 accepted and committed: Started Litra Beam support. Added early “litra” heuristic in classify_device_kind so Litra Beam devices are reliably classified as “other” (non-mouse, non-keyboard) with clear detection logging. Zero impact on existing mouse/keyboard paths. Passed Code Review + AC validation.
- TASK-008 micro-chunk 008.2 accepted and committed: Basic illumination control skeleton for Litra Beam (host-side on/off + brightness). Added feature detection + set/read methods in the listener and thin public wrappers on Engine (following keyboard middle-path pattern). All changes clearly temporary/host-side only and safe for non-Litra devices. Passed Code Review + AC validation.
- TASK-008 micro-chunk 008.3 accepted and committed: Thin Backend exposure for Litra Beam illumination (`setLitraIllumination` / `readLitraIllumination` as thin delegates, with clear host-side/temporary docstrings and safe defaults). Completes the same exposure pattern used for keyboard middle-path methods. Passed Code Review + AC validation.
- TASK-008 micro-chunk 008.4 accepted and committed: Added minimal test coverage (`LitraIlluminationBackendTests`) for the new Backend methods (safe no-engine defaults + delegation) and confirmed they are directly callable from the existing debug surface. Completes the “via debug methods at minimum” requirement. Passed Code Review + AC validation.
- TASK-008 micro-chunk 008.5 accepted and committed: First minimal user-facing Litra Beam UI. Added tiny `hasLitraBeam` property in Backend + new `LitraControls.qml` card (On/Off + brightness with temporary warning). Placed as conditional sibling after the context-aware keyboard footer in Main.qml. First real user-facing Litra experience. Passed Code Review + AC validation.
- TASK-008 micro-chunk 008.6 accepted and committed: Polish & robustness for the Litra Beam card (device-change reactivity, refreshing state + indicator, auto-clearing error feedback, 350 ms slider debounce). Brings the first Litra UI experience to the same level as the polished keyboard controls. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.1 accepted and committed: First disciplined step toward the cleaner LogitechDevice / FeatureHandler architecture. Added minimal base classes + extracted Litra illumination behind a concrete handler. Public Engine API and all existing behavior remain 100% unchanged. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.2 accepted and committed: Extracted Battery (read + result handling) into BatteryHandler. Wired delegation in the Engine polling loop with lazy attachment and full fallback to the original path. Public battery API and all callbacks remain 100% unchanged. Second feature extraction on an established, cross-device capability. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.3 accepted and committed: Extracted SmartShift (read + write + state) into SmartShiftHandler. Wired delegation in the main SmartShift entry points on Engine with lazy attachment and full fallback. Higher-level toggle/switch helpers automatically benefit. Public API and all callbacks remain 100% unchanged. Third feature extraction on a stateful, interactive capability. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.4 accepted and committed: Extracted DPI (core set/read) into DPIHandler. Wired delegation in `set_dpi()` with lazy attachment and full fallback. `_cycle_dpi` and preset logic remain in Engine. Public DPI API and all related behavior remain 100% unchanged. Fourth feature extraction on a core, high-frequency mouse capability. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.5 accepted and committed: Extracted Report Rate (read + set) into ReportRateHandler. Wired delegation in Engine via thin public wrappers with lazy attachment and full fallback. Public Report Rate API and all existing behavior remain 100% unchanged. Fifth feature extraction on a clean, cross-device capability. Passed Code Review + AC validation.

For the detailed current task board, see [docs/TASKS.md](docs/TASKS.md).  
For overall status and roadmap, see [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md).

---

## Legacy Mouse Remapper Documentation

The original Mouser functionality for remapping Logitech mice is still fully supported and remains high quality.

For the classic documentation (features, supported mice, default mappings, etc.), please refer to the previous version of this README or the files in the repository history.

**Note:** As the project evolves, the primary documentation is moving toward the new `docs/` directory.

---

## Contributing & Working Style

We work in **small, reviewable micro-chunks** using a task-driven process:

- Tasks are defined with clear Description, Requirements, and Acceptance Criteria (see `docs/TASKS.md`).
- Implementation is done in focused changes.
- Specialized sub-agents act as expert reviewers and gatekeepers. A task is only marked "Done" after it passes code review and acceptance criteria validation.
- We prioritize "Onboard is Sacred" and the "Middle Path" philosophy on every change.

---

## License

This project is licensed under the MIT License.

**Mouser** is not affiliated with or endorsed by Logitech. "Logitech", "MX Master", "G502", and "Options+" are trademarks of Logitech International S.A.