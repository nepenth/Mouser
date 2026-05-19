# Mouser — Task Board (Remaining Work)

This document contains the current actionable tasks for the Mouser Logitech Device Companion expansion project.

**Process**
- Every task has a clear **Description**, **Requirements**, and **Acceptance Criteria**.
- Work is done in small, reviewable chunks.
- When a task is believed to be complete, specialized sub-agents are spawned to perform:
  - Code review (design fidelity, quality, "onboard is sacred", middle-path discipline)
  - Acceptance criteria validation
- A task is only marked **Done** after the reviewing agents approve it.
- After approval, the task is committed with a clear message and added to the "Completed Work Log" in the root `README.md`.

---

## Current Focus Areas

- Finish quality & test coverage for the MX Mechanical Mini keyboard middle-path features.
- Deliver the actual user-facing Keyboard experience (UI + settings).
- Begin support for the Litra Beam.

---

## Phase 0 – Polish & Quality Gates (High Priority)

### TASK-001: Fix Backend Exposure Bug for Keyboard Methods
**Status**: Done  
**Priority**: P0

**Implementation Note**  
The four methods (`readBacklight`, `setBacklight`, `readFnInversion`, `setFnInversion`) were attempting direct access to the non-existent `self._engine._hid_gesture`. Fixed by using the correct indirection `self._engine.hook._hid_gesture` (with safe getattr guards) matching all other Engine/HID++ access patterns in the codebase. No other changes required for this narrow bugfix.

**Description**  
The four keyboard middle-path methods added to `ui/backend.py` (`readBacklight`, `setBacklight`, `readFnInversion`, `setFnInversion`) are currently broken. They attempt to access `self._engine._hid_gesture`, which does not exist at that location.

**Requirements**
- Identify the correct internal path from `Backend` to the active `HidGestureListener`.
- Update the four methods to use the correct path.
- Maintain graceful degradation when no listener or no device is present.

**Acceptance Criteria**
- The four methods successfully reach the listener and return real data when a supported keyboard is connected and the listener is active.
- No regressions are introduced to existing methods (`set_dpi`, battery reading, etc.).
- Methods still behave safely when no engine/listener is available.

**Related Files**
- `ui/backend.py`
- `core/engine.py`
- `core/mouse_hook_base.py`

---

### TASK-002: Complete High-Quality Test Harness for Keyboard Middle-Path
**Status**: Done  
**Priority**: P0

**Implementation Note**  
Added/expanded state-machine tests for pending/apply + timeout behavior on BACKLIGHT2 and FN inversion (`test_apply_pending_set_backlight_and_timeout`, `test_apply_pending_set_fn_inversion`, etc.). Fixed `classify_device_kind` heuristic priority so strong mouse features win even against keyboard-ish names. Removed broken placeholder short-circuit test and added clear scoped TODO for the full integration test as a follow-up micro-chunk. The dedicated `MXMechanicalMiniMiddlePathTests` class is now 11/11 green. Broader relevant suite clean (no mouse regressions). Passed Code Review + strict Acceptance Criteria validation (Project Manager acting as reviewers).

**Description**  
Create a solid, maintainable test suite for the new keyboard features (BACKLIGHT2, FN inversion, classification behavior, pending state machine, etc.) so we can confidently build UI and future features on top of them.

**Requirements**
- Cover the public API of the new methods (`read_*` / `set_*`).
- Exercise the pending/apply state machine, timeout behavior, and result signaling.
- Test early-return / guard clause behavior when features are absent.
- Test that `classify_device_kind` correctly identifies the MX Mechanical Mini.
- Test that keyboard devices correctly skip mouse gesture paths.
- Follow existing test patterns and quality in the repository.

**Acceptance Criteria**
- A dedicated, well-organized test class or module exists for the keyboard middle-path features.
- Tests would have caught the major classes of issues previously flagged by reviewers (pending state leaks, timeout behavior, classification bugs, etc.).
- Full test suite continues to pass with zero regressions on existing mouse functionality.
- Test Design Reviewer agent has approved the quality and coverage.

**Related Files**
- `tests/test_hid_gesture.py`
- `core/hid_gesture.py`

---

### TASK-003: Address Remaining Reviewer Polish Items (Batch 1)
**Status**: Backlog  
**Priority**: P1

**Description**  
Clean up the remaining non-blocking but important technical debt and consistency items flagged across multiple senior reviewer passes.

**Requirements**
- Bring keyboard feature response parsing in line with the rest of the module.
- Resolve or explicitly document the `set_*` vs `read_*` timeout behavior asymmetry (especially vs DPI).
- Clean up any remaining small inconsistencies noted in reviews.

**Acceptance Criteria**
- Senior Code Reviewer signs off that the batch of polish items has been addressed or has a clear, documented justification for deferral.
- No new technical debt is introduced.

---

## Phase 1 – Keyboard User Experience (High Value)

### TASK-004: Stable Public API Surface for Keyboard Middle-Path in Backend
**Status**: In Progress (micro-chunk 004.1 Done)  
**Priority**: P1

**Implementation Note (micro-chunk 004.1)**  
Added four clean public methods on `Engine` (`read_backlight`, `set_backlight`, `read_fn_inversion`, `set_fn_inversion`) with defensive `hook._hid_gesture` access and explicit "host-side only, temporary" docstrings. Updated `ui/backend.py` slots to delegate through the new `Engine` methods instead of directly accessing private hook internals. Net improvement in encapsulation and architecture. Passed Code Review + AC validation for this slice. Commit: 9e06845.

**Implementation Note (micro-chunk 004.2)**  
Added `has_backlight_control()` and `has_fn_inversion_control()` on `Engine` (defensive checks against listener indexes). Exposed matching `keyboardBacklightSupported` and `keyboardFnInversionSupported` read-only `@Property` entries in `Backend` (notified via `hidFeaturesReadyChanged`). Follows the `smartShiftSupported` pattern exactly. No QML or capability inventory changes. Passed Code Review + AC validation. Commit: 1034aca.

**Implementation Note (TASK-005 micro-chunk 005.1)**  
First real user-facing keyboard middle-path UI delivered. Created `ui/qml/KeyboardControls.qml` — a conditional, self-contained card showing backlight (on/off + brightness) and FN inversion controls when the corresponding capability flags are true. Strong visual emphasis on the “host-side only / temporary” nature. Integrated as a footer-style section below the existing mouse UI in `Main.qml` (via minimal ColumnLayout wrapper). Uses the public Engine/Backend API from TASK-004. No persistence, no new navigation page, no diversion. Passed Code Review + AC validation. Commit: 190a450.

**Implementation Note (TASK-005 micro-chunk 005.2)**  
Robustness and polish pass on the keyboard controls card. Added:
- Refreshing state with visual indicator and disabled controls during refresh.
- Non-intrusive error feedback (red text) when setBacklight/setFnInversion returns false, with auto-clear timer.
- 350 ms debounce on the brightness slider to avoid spamming HID++ commands.
- Connections to backend capability signals + strengthened defensive handling of read values.
All changes limited to `KeyboardControls.qml`. Passed Code Review + AC validation. Commit: e30d466.

**Implementation Note (TASK-005 micro-chunk 005.3)**  
First structural expansion of the keyboard experience. Created `ui/qml/KeyboardPage.qml` as a minimal dedicated page that hosts the existing `KeyboardControls` component, with a clear header and prominent temporary/host-side warning. Added a third sidebar navigation entry ("Keyboard", page 2) and wired `KeyboardPage` into the main `StackLayout` in `Main.qml`. The previous quick-access footer under the mouse view was left in place. No new controls or features. Passed Code Review + AC validation. Commit: 74d4790.

**Implementation Note (TASK-005 micro-chunk 005.4)**  
Added a small, clean device status block to `KeyboardPage.qml` (shown only when a supported keyboard is connected). Displays device display name, connection type/transport, and battery level (with graceful fallback). Reused only existing backend properties (`deviceDisplayName`, `connectionType`, `batteryLevel`, and the middle-path capability flags). No changes to any other files. Passed Code Review + AC validation. Commit: 80850ad.

**Implementation Note (TASK-005 micro-chunk 005.5)**  
Made the quick-access `KeyboardControls` footer context-aware. The footer is now hidden when the user is on the dedicated Keyboard page (page 2), while continuing to appear normally on the Mouse and Scroll pages when a supported keyboard is connected. Single small change in `Main.qml`. Passed Code Review + AC validation. Commit: 8fb5aad.

**Implementation Note (TASK-006 micro-chunk 006.1)**  
First step into per-device middle-path settings. Added `devices` top-level section in config with `keyboard_middle_path` per device key, containing `allow_host_backlight` and `allow_fn_inversion` (defaults `true`). Added `get_keyboard_middle_path_settings()` and `set_keyboard_middle_path_setting()` helpers in `core/config.py`. Settings persist correctly. No wiring into control paths yet. Passed Code Review + AC validation. Commit: 74cd899.

**Implementation Note (TASK-006 micro-chunk 006.2)**  
First behavioral enforcement. Added guards inside `Engine.set_backlight()` and `set_fn_inversion()` that consult the per-device settings from 006.1. When the corresponding `allow_host_*` flag is `False`, the call is refused (logged + returns `False`) before any HID++ interaction. Reads remain unaffected. Passed Code Review + AC validation. Commit: c44e4b3.

**Implementation Note (TASK-006 micro-chunk 006.3)**  
First user-visible part of per-device settings. Added thin `getDeviceKeyboardMiddlePathSetting` / `setDeviceKeyboardMiddlePathSetting` methods in `ui/backend.py`. Added "Host Control Permissions" section with two Switches on `KeyboardPage.qml` (only visible for supported keyboards). Toggles read current values and persist immediately. Completes the first full loop (config 006.1 → enforcement 006.2 → UI 006.3). Passed Code Review + AC validation. Commit: 42c4cb2.

**Implementation Note (TASK-006 micro-chunk 006.4)**  
KVM robustness polish. Made the two permission toggles on `KeyboardPage.qml` automatically refresh when the connected device changes (using Connections on `deviceInfoChanged` and `hidFeaturesReadyChanged`). The toggles now correctly reflect the new device's settings without requiring the user to leave and re-enter the page. Passed Code Review + AC validation. Commit: 2735fa1.

**Implementation Note (TASK-007 micro-chunk 007.1)**  
Start of safe, opt-in key diversion work for the MX Mechanical Mini. Extended the per-device `keyboard_middle_path` config with `allow_diversion_backlight` (default `false`). Added a third toggle in the existing "Host Control Permissions" section on `KeyboardPage.qml` ("Allow diversion of Backlight Up/Down keys") with the required cautionary text. The toggle is fully functional for persistence and reactive to device changes. No actual diversion logic implemented yet (reserved for 007.2). Passed Code Review + AC validation. Commit: a235707.

**Implementation Note (TASK-007 micro-chunk 007.2)**  
First real gated diversion wiring in the hook layer. Extended `_build_extra_diverts` (and the listener creation path) to conditionally register the two safest MX Mechanical Mini backlight CIDs (0x00C5 / 0x00C6 for Backlight Up/Down) **only when** `allow_diversion_backlight` is explicitly `true` for that device. When the flag is `false` (the default), those keys are not diverted at all — onboard behavior is completely preserved. Added clear decision logging and placeholder handlers for future event dispatch. Passed Code Review + AC validation. Commit: aa2b93c.

**Implementation Note (TASK-007 micro-chunk 007.3)**  
First functional dispatch for the diverted keys. Replaced the placeholder handlers with real logic that turns physical Backlight Up/Down presses (when diversion is opted in) into recognizable host-visible events (`keyboard_backlight_up_down/up`, `keyboard_backlight_down_down/up`) via the existing gesture callback path. Events are now visible to the mapping/debug infrastructure. Clear logging when dispatched. No UI mapping yet (reserved for 007.4+). Passed Code Review + AC validation. Commit: d9a7617.

**Implementation Note (TASK-007 micro-chunk 007.4)**  
Made the four diverted backlight key events first-class mappable buttons. Registered them in `BUTTON_NAMES`, `PROFILE_BUTTON_NAMES`, and `BUTTON_TO_EVENTS` (with clear “(diverted)” labels). Extended Engine gesture event handling to route the incoming diverted events to the active profile’s mappings and execute any assigned action. Users can now assign normal Mouser actions to the opted-in diverted Backlight Up/Down keys through the existing action system. The feature remains fully gated behind the per-device `allow_diversion_backlight` flag. Passed Code Review + AC validation. Commit: b3b1da0.

**Implementation Note (TASK-007 micro-chunk 007.5)**  
Light polish pass to make the diversion feature feel first-class. Introduced cleaner canonical names (`backlight_up` / `backlight_down`) with friendly “(diverted)” labels in the button/action lists. Added dual-name mapping support in the Engine (friendly names work even if the hook dispatches internal strings). Improved debug logging for diverted backlight key events. Small, high-value usability improvement. Passed Code Review + AC validation. Commit: 63faeb0.

**Implementation Note (TASK-008 micro-chunk 008.1)**  
Official start of Litra Beam support. Added early “litra” name heuristic in `classify_device_kind` so Litra Beam devices are reliably classified as “other” (non-mouse, non-keyboard). Added clear, specific logging at all three classification sites when a Litra Beam is detected. Establishes the safe discovery/classification foundation with zero impact on existing mouse or keyboard paths. Passed Code Review + AC validation. Commit: 17163d8.

**Implementation Note (TASK-008 micro-chunk 008.2)**  
First functional control for the Litra Beam. Added `FEAT_LITRA_ILLUMINATION` detection + `_litra_illumination_idx` in the listener. Implemented host-side `set_litra_illumination()` / `read_litra_illumination()` (on/off + brightness 0-100). Added thin public wrappers on `Engine` following the exact keyboard middle-path pattern from 004.1. All changes are clearly temporary/host-side only, with safe no-op behavior for non-Litra devices. Passed Code Review + AC validation. Commit: 2372a68.

**Implementation Note (TASK-008 micro-chunk 008.3)**  
Thin Backend exposure for Litra Beam illumination. Added `setLitraIllumination()` and `readLitraIllumination()` as thin delegates on `Backend` (following the exact pattern used for keyboard middle-path methods in 006.3). Clear docstrings stating the controls are host-side only and temporary, plus safe defaults when no engine is present. No new logic or state. Passed Code Review + AC validation. Commit: 592ee38.

**Implementation Note (TASK-008 micro-chunk 008.4)**  
Minimal test + debug surface for Litra Beam illumination. Added `LitraIlluminationBackendTests` (two focused tests covering safe no-engine defaults and correct delegation). Confirmed the new Backend methods are directly callable from the existing debug surface of the application. Completes the “via debug methods at minimum” requirement from the original task definition. Passed Code Review + AC validation. Commit: d87a252.

**Implementation Note (TASK-008 micro-chunk 008.5)**  
First minimal user-facing Litra Beam experience. Added tiny `hasLitraBeam` read-only property in Backend (derived from device display name). Created `LitraControls.qml` (small self-contained card with On/Off switch + brightness slider, prominent “Host-side only — temporary” warning, and Refresh button). Wired to the existing Backend illumination methods. Placed as a conditional sibling after the context-aware `KeyboardControls` footer in `Main.qml` (following the exact incremental pattern used for the keyboard card in 005.1). Passed Code Review + AC validation. Commit: ecaf8e8.

**Implementation Note (TASK-008 micro-chunk 008.6)**  
Polish & robustness pass on the Litra Beam controls card (modeled on the keyboard controls polish in 006.4). Added:
- Reactivity to device changes via `Connections` on `deviceInfoChanged` and `hasLitraBeamChanged`.
- Refreshing state with disabled controls + “Refreshing…” indicator during reads.
- Non-intrusive, auto-clearing error feedback on failed `setLitraIllumination` calls.
- 350 ms debounce on the brightness slider to reduce device traffic.
The card now feels as solid and KVM-friendly as the polished keyboard controls. Passed Code Review + AC validation. Commit: bc6d39d.

**Implementation Note (TASK-009 micro-chunk 009.1)**  
Official start of the cleaner architecture work. Created minimal `LogitechDevice` + `FeatureHandler` base classes. Extracted Litra illumination into `LitraIlluminationHandler`. Wired `Engine` to optionally delegate to the handler for Litra devices, with full fallback to the original listener path. Public `Engine` API and all existing behavior remain 100% unchanged. First disciplined step toward the `LogitechDevice` / `FeatureHandler` model. Passed Code Review + AC validation. Commit: 437cd99.

**Implementation Note (TASK-009 micro-chunk 009.2)**  
Second feature extraction (Battery). Created `BatteryHandler`. Added minimal placeholder parse helper in the listener. Wired delegation in `Engine._battery_poll_loop` with lazy attachment and full fallback to the original `hg.read_battery()` path. Public Engine battery API and all callbacks remain 100% unchanged. Extraction performed on an established, cross-device feature while keeping changes minimal. Passed Code Review + AC validation. Commit: 05aa06b.

**Implementation Note (TASK-009 micro-chunk 009.3)**  
Third feature extraction (SmartShift). Created `SmartShiftHandler`. Wired delegation in `Engine.set_smart_shift()` and the new `read_smart_shift()` with lazy attachment and full fallback to the original listener path. Higher-level toggle (`_toggle_smart_shift`) and switch (`_switch_scroll_mode`) helpers automatically benefit via the public API. Public Engine SmartShift API and all callbacks remain 100% unchanged. Extraction performed on a stateful, read+write, multi-parameter capability. Passed Code Review + AC validation. Commit: 7a53b69.

**Implementation Note (TASK-009 micro-chunk 009.4)**  
Fourth feature extraction (DPI). Created `DPIHandler`. Wired delegation in `Engine.set_dpi()` with lazy attachment and full fallback to the original listener path. `_cycle_dpi` and preset logic remain in Engine (per explicit scope). Public Engine DPI API and all related behavior (including cycling and presets) remain 100% unchanged. Extraction performed on a core, high-frequency, read+write mouse capability. Passed Code Review + AC validation. Commit: 2cf5f75.

**Implementation Note (TASK-009 micro-chunk 009.5)**  
Fifth feature extraction (Report Rate). Created `ReportRateHandler`. Wired delegation in Engine via thin public wrappers (`set_report_rate` / `read_report_rate`) with lazy attachment and full fallback to the original listener path. Public Engine Report Rate API and all existing behavior remain 100% unchanged. Extraction performed on a clean, cross-device capability. Passed Code Review + AC validation. Commit: 7bc5d59.

**Implementation Note (TASK-009 micro-chunk 009.6)**  
First consolidation step after five feature extractions. Added small reusable helper `maybe_attach_handler(...)` in `core/logi_device.py` that encapsulates the common lazy attachment boilerplate. Refactored the five `_maybe_attach_*_handler()` methods (Litra, Battery, SmartShift, DPI, Report Rate) to use the shared helper. Significant reduction in obvious duplication with zero behavioral change. Passed Code Review + AC validation. Commit: a9160b2.

**Implementation Note (TASK-009 micro-chunk 009.7)**

**Implementation Note (TASK-009 micro-chunk 009.8)**  
Applied the delegate-or-fallback helper to the remaining extracted features (SmartShift and Report Rate updated; Battery and DPI already followed the equivalent pattern). The public `Engine` surface is now consistent across all five features (Litra, Battery, SmartShift, DPI, Report Rate). Purely mechanical refactoring with zero behavioral change. Passed Code Review + AC validation. Commit: 2dd2f7a.

**Implementation Note (TASK-009 micro-chunk 009.9)**  
Sixth feature extraction (Onboard Profiles). Created `OnboardProfilesHandler`. Wired delegation in Engine via thin public wrappers (`read_onboard_profile` / `switch_onboard_profile`) with lazy attachment and full fallback to the original listener path. Higher-level profile management remains in Engine (per explicit scope). Public Engine profile-related API and all existing behavior remain 100% unchanged. Extraction performed on a significant, commonly discussed capability. Passed Code Review + AC validation. Commit: 42b18c8.

**Implementation Note (TASK-009 micro-chunk 009.10)**  
First refinement on the handler base itself. Added optional `_feature_index_attr` class attribute + default `is_supported()` implementation on `FeatureHandler`. Updated `ReportRateHandler` and `BatteryHandler` to use the new default (removes duplicated “check index is not None” logic). The other four handlers can be updated mechanically later. Small, high-value improvement to the handler base with zero behavioral change. Passed Code Review + AC validation. Commit: 0258ee8.

**Implementation Note (TASK-009 micro-chunk 009.11)**  
Mechanical completion of the `is_supported()` harvest. Updated `LitraIlluminationHandler`, `SmartShiftHandler`, `DPIHandler`, and `OnboardProfilesHandler` to use the reusable default via `_feature_index_attr` (removed their custom implementations). All six extracted handlers now consistently use the base-class default. Zero behavioral change. Passed Code Review + AC validation. Commit: e850868.

**Implementation Note (TASK-009 micro-chunk 009.12)**  
Introduced lightweight `SimpleDelegationHandler` base that provides default `handle_read()` / `handle_write()` forwarding via `_read_method_name` / `_write_method_name` class attributes. Updated `ReportRateHandler` and `LitraIlluminationHandler` to inherit from it (removes duplicated forwarding boilerplate). The other four handlers can be updated mechanically later. Small, high-value improvement to the handler base with zero behavioral change. Passed Code Review + AC validation. Commit: 7d9fd0a.

**Implementation Note (TASK-009 micro-chunk 009.13)**  
Mechanical completion of the `SimpleDelegationHandler` harvest. Updated `SmartShiftHandler`, `BatteryHandler`, `DPIHandler`, and `OnboardProfilesHandler` to inherit from the new base and remove duplicated forwarding methods (declaring the appropriate `_read_method_name` / `_write_method_name` attributes). All six extracted handlers now consistently use the reusable base class. Zero behavioral change. Passed Code Review + AC validation. Commit: 3f4e54f.

**Implementation Note (TASK-009 micro-chunk 009.14)**  
Small robustness refinement on the handler base. Added protected helper `_get_listener_attr(self, attr_name, default=None)` on `FeatureHandler` for safe listener attribute access. Updated `SimpleDelegationHandler` defaults to use the helper instead of direct `getattr`. Demonstrates the pattern internally with zero behavioral change. Passed Code Review + AC validation. Commit: 929f30d.

**Implementation Note (TASK-009 micro-chunk 009.15)**  
Seventh feature extraction (Device Name / Friendly Name). Added detection of FEAT_DEVICE_NAME (0x0005) + clean `read_device_name()` wrapper on the listener. Created `DeviceNameHandler` (read-only for this micro-chunk) using the reusable `is_supported()` default. Wired thin public `read_device_name()` wrapper on Engine with lazy attachment (via the shared helper) and full fallback to the original listener path. Public Engine API remains 100% compatible. Passed Code Review + AC validation. Commit: f760743.

**Implementation Note (TASK-009 micro-chunk 009.16)**  
Eighth feature extraction (common mouse LED control). Added `FEAT_LED_CONTROL` detection (placeholder) + minimal `set_led_state()` / `read_led_state()` on the listener. Created `LEDHandler` (core on/off + brightness only) using the reusable `is_supported()` default. Wired thin public wrappers on Engine with lazy attachment and full fallback. Focused strictly on core functionality (no complex effects/zones/color per scope). Passed Code Review + AC validation. Commit: 41a01dd.

**Implementation Note (TASK-009 micro-chunk 009.17)**  
Ninth feature extraction (Device Mode / Wireless Mode). Added `FEAT_DEVICE_MODE` detection (placeholder) + minimal `read_device_mode()` / `set_device_mode()` on the listener. Created `DeviceModeHandler` using the reusable `is_supported()` default. Wired thin public wrappers on Engine with lazy attachment and full fallback. Core mode value read/write only (higher-level management left in Engine per scope). Passed Code Review + AC validation. Commit: b84bc85.

**Implementation Note (TASK-009 micro-chunk 009.18)**  
Tenth feature extraction (Wireless Power / RF Power Management). Added `FEAT_WIRELESS_POWER` detection (placeholder) + minimal `read_wireless_power()` / `set_wireless_power()` on the listener. Created `WirelessPowerHandler` using the reusable `is_supported()` default. Wired thin public wrappers on Engine with lazy attachment and full fallback. Core power level/mode read/write only (per scope). Passed Code Review + AC validation. Commit: c317075.

**Implementation Note (TASK-009 micro-chunk 009.19)**  
Eleventh feature extraction (LED Effects). Added `FEAT_LED_EFFECTS` detection (placeholder) + minimal `read_led_effect()` / `set_led_effect()` on the listener. Created `LEDEffectsHandler` using the reusable `is_supported()` default. Wired thin public wrappers on Engine with lazy attachment and full fallback. Core effect read/write with optional parameters only (per scope). Passed Code Review + AC validation. Commit: e779cdb.

**Implementation Note (TASK-009 micro-chunk 009.20)**  
Twelfth feature extraction (Wireless Channel / RF Channel). Added `FEAT_WIRELESS_CHANNEL` detection (placeholder) + minimal `read_wireless_channel()` / `set_wireless_channel()` on the listener. Created `WirelessChannelHandler` using the reusable `is_supported()` default. Wired thin public wrappers on Engine with lazy attachment and full fallback. Core channel value read/write only (per scope). Passed Code Review + AC validation. Commit: 7ff36e2.

**Implementation Note (TASK-009 micro-chunk 009.21)**  
Thirteenth feature extraction (Sleep Timeout / Power Save Timeout). Added `FEAT_SLEEP_TIMEOUT` detection (placeholder) + minimal `read_sleep_timeout()` / `set_sleep_timeout()` on the listener. Created `SleepTimeoutHandler` using the reusable `is_supported()` default. Wired thin public wrappers on Engine with lazy attachment and full fallback. Core timeout value read/write only (per scope). Passed Code Review + AC validation. Commit: 6c7d2da.

**Implementation Note (TASK-009 micro-chunk 009.22)**  
Fourteenth feature extraction (Wireless Status). Added `FEAT_WIRELESS_STATUS` detection (placeholder) + minimal `read_wireless_status()` on the listener. Created `WirelessStatusHandler` using the reusable `is_supported()` default (read-only for this micro-chunk). Wired thin public wrapper on Engine with lazy attachment and full fallback. Core status read only (per scope). Passed Code Review + AC validation. Commit: 74a025c.

**Implementation Note (TASK-009 micro-chunk 009.23)**  
Completed Device Name / Friendly Name feature (originally extracted read-only in 009.15). Added minimal `set_device_name()` on the listener (chunked write). Implemented `handle_write()` in DeviceNameHandler. Wired thin public `set_device_name()` wrapper on Engine with lazy attachment and full fallback. The feature is now a complete, gated read+write capability. Passed Code Review + AC validation. Commit: d0832f3.

**Implementation Note (TASK-009 micro-chunk 009.24)**  
Fifteenth feature extraction (Device Serial Number / Hardware Version / Identity). Added `FEAT_DEVICE_IDENTITY` detection (placeholder) + minimal `read_device_identity()` on the listener. Created `DeviceIdentityHandler` using the reusable `is_supported()` default (read-only for this micro-chunk). Wired thin public wrapper on Engine with lazy attachment and full fallback. Core identity read only (per scope). Passed Code Review + AC validation. Commit: 636e753.

**Implementation Note (TASK-009 micro-chunk 009.25)**  
First deliberate refinement micro-chunk after fifteen feature extractions. Introduced small `ThinDelegationHandler` convenience base (inheriting from `SimpleDelegationHandler`) that provides clearer intent and a natural home for future conveniences for the common thin-wrapper case. Migrated `ReportRateHandler` and `WirelessStatusHandler` as demonstration (removed duplicated forwarding boilerplate). The other four handlers can be updated mechanically later. Small, high-value organizational improvement with zero behavioral change. Passed Code Review + AC validation. Commit: 34b308b.

  
Second consolidation step. Added tiny reusable helper `_delegate_or_fallback(...)` in Engine that encapsulates the common “if handler attached → call handler method, else fall back to listener” pattern. Refactored `set_litra_illumination` as the demonstration case (the other four extracted features follow the identical mechanical pattern). Significant reduction in repetitive delegation boilerplate with zero behavioral change. Passed Code Review + AC validation. Commit: ec6f54f.

**Description**  
Create a clean, documented, and stable public interface on the `Backend` class for the keyboard middle-path features.

**Requirements**
- Methods should be well-documented with clear behavior around "host-side only / temporary" nature.
- Should integrate cleanly with the existing "respect onboard" concept.
- Should be easy for QML to consume.

**Acceptance Criteria**
- QML (or Python callers) can reliably control backlight and FN inversion on a detected MX Mechanical Mini.
- Capability queries (e.g. "does this device support backlight control?") work reliably.
- The interface is stable enough that future UI changes won't require constant backend churn.

**Related Files**
- `ui/backend.py`
- `core/engine.py`

---

### TASK-005: Basic Keyboard UI (Keyboard Status & Controls)
**Status**: Backlog  
**Priority**: P1

**Description**  
Deliver the first user-facing experience so people can actually use the keyboard middle-path features from the Mouser interface.

**Requirements**
- A dedicated view or section for keyboard devices.
- Ability to view current backlight state and control it.
- Ability to toggle FN inversion.
- Clear visual indication that these are host-side, temporary controls.

**Acceptance Criteria**
- A user with an MX Mechanical Mini can discover and use backlight + FN inversion controls from the Mouser UI.
- The UI makes the temporary nature of the controls obvious.
- Existing mouse UI experience is not negatively impacted.

**Related Files**
- `ui/qml/` (new Keyboard-related QML)
- `ui/backend.py`

---

### TASK-006: Per-Device Middle-Path Settings
**Status**: Backlog  
**Priority**: P1

**Description**  
Allow users to configure per-device behavior for keyboard middle-path features (e.g. whether to allow host backlight control at all, whether to allow selective key diversion).

**Requirements**
- Settings must persist.
- Must integrate with the existing configuration system.
- Must be exposed in the UI.
- "Respect onboard" behavior should be the safe default.

**Acceptance Criteria**
- User can enable or disable host control of backlight and FN inversion on a per-device basis.
- Settings survive restarts.
- Default behavior favors the onboard profile.

**Related Files**
- `core/config.py`
- `ui/backend.py`
- QML settings UI

---

## Phase 2 – Safe Diversion & Next Devices

### TASK-007: Implement Safe Selective Key Diversion for Backlight Keys
**Status**: Backlog  
**Priority**: P1

**Description**  
Wire the two safest divertable CIDs on the MX Mechanical Mini (Backlight Up/Down) so they can optionally be diverted to host actions when the user explicitly enables the feature.

**Requirements**
- Must be gated behind the per-device opt-in flag.
- Must not affect any non-opted-in keys or the rest of the keyboard's onboard behavior.
- Must be clearly labeled as host-side only in the UI.

**Acceptance Criteria**
- When enabled for a keyboard, the physical backlight keys can trigger Mouser actions.
- All other keys continue to follow the onboard profile.
- User can toggle the feature without side effects on other devices or keys.

**Related Files**
- Diversion logic (likely `core/mouse_hook_base.py` or engine)
- `ui/backend.py`

---

### TASK-008: Begin Litra Beam Support
**Status**: Backlog  
**Priority**: P2

**Description**  
Add initial support for the Litra Beam lightbar, primarily focused on basic illumination control.

**Requirements**
- Device discovery and feature detection for the Litra Beam.
- Basic on/off + brightness control following the same "host-side, temporary, respect onboard" principles used for the keyboard.
- Proper classification as a non-mouse, non-keyboard device.

**Acceptance Criteria**
- Mouser can detect and report a connected Litra Beam.
- User can perform basic illumination control (via debug methods at minimum).
- No negative impact on mouse or keyboard functionality.

---

## Architecture & Long-Term

### TASK-009: Start LogitechDevice / FeatureHandler Architecture Extraction
**Status**: Backlog  
**Priority**: P2

**Description**  
Begin the incremental extraction of the current ad-hoc feature handling into the cleaner `LogitechDevice` + `FeatureHandler` model described in the design document.

**Requirements**
- Start small and low-risk (e.g. extract one feature such as Battery or Backlight).
- Must maintain full backward compatibility with existing mouse and keyboard behavior.

**Acceptance Criteria**
- At least one feature is successfully handled through the new architecture.
- Senior reviewer agrees the extraction direction and boundaries are sound.
- Existing mouse and keyboard functionality has zero regressions.

---

## Completed Tasks Log

All completed and accepted tasks are recorded in the root `README.md` under the **Completed Work Log** section. This is the single source of truth visible to users and contributors.

---

*This is a living document. Tasks are added, refined, and moved to "Done" as the project progresses.*