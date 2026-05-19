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