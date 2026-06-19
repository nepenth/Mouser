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
- TASK-009 micro-chunk 009.6 accepted and committed: Introduced small reusable helper `maybe_attach_handler(...)` in `core/logi_device.py` and refactored the five attachment methods to use it (significant duplication reduction, zero behavioral change). First consolidation step after five feature extractions. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.7 accepted and committed: Introduced shared helper `_delegate_or_fallback(...)` in Engine for the common delegate-or-fallback pattern in public methods. Refactored `set_litra_illumination` as the demonstration case (the other four follow the identical mechanical pattern). Significant reduction in repetitive boilerplate with zero behavioral change. Passed Code Review + AC validation.

- TASK-009 micro-chunk 009.8 accepted and committed: Applied the delegate-or-fallback helper to the remaining extracted features (SmartShift and Report Rate updated; Battery and DPI already followed the equivalent pattern). The public `Engine` surface is now consistent across all five features (Litra, Battery, SmartShift, DPI, Report Rate). Purely mechanical refactoring with zero behavioral change. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.9 accepted and committed: Extracted basic Onboard Profile switching (read + switch) into OnboardProfilesHandler. Wired delegation in Engine via thin public wrappers with lazy attachment and full fallback. Higher-level profile management remains in Engine. Public profile-related API remains 100% unchanged. Sixth feature extraction on a significant, commonly discussed capability. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.10 accepted and committed: Added reusable `is_supported()` default in `FeatureHandler` base via optional `_feature_index_attr`. Updated ReportRateHandler and BatteryHandler to use it (removes duplicated “check index is not None” logic). Small, high-value improvement to the handler base with zero behavioral change. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.11 accepted and committed: Updated the remaining four handlers (Litra, SmartShift, DPI, Onboard Profiles) to use the default `is_supported()` via `_feature_index_attr`. All six handlers now consistently use the base-class default. Zero behavioral change. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.12 accepted and committed: Introduced lightweight `SimpleDelegationHandler` base for thin-wrapper forwarding. Updated ReportRateHandler and LitraIlluminationHandler to inherit from it (removes duplicated forwarding boilerplate). The other four can be updated mechanically later. Small, high-value improvement with zero behavioral change. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.13 accepted and committed: Updated the remaining four handlers (SmartShift, Battery, DPI, Onboard Profiles) to inherit from `SimpleDelegationHandler` and remove duplicated forwarding methods. All six handlers now consistently use the reusable base class. Zero behavioral change. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.14 accepted and committed: Introduced protected helper `_get_listener_attr(...)` on `FeatureHandler` for safe listener attribute access. Updated `SimpleDelegationHandler` defaults to use it. Small, high-value robustness improvement with zero behavioral change. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.15 accepted and committed: Extracted basic Device Name / Friendly Name support into DeviceNameHandler (seventh extraction). Wired thin public `read_device_name()` wrapper on Engine with full fallback. Handler is read-only for this micro-chunk (per scope). Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.16 accepted and committed: Extracted basic mouse LED control (on/off + brightness) into LEDHandler (eighth extraction). Wired thin public `set_led_state()` / `read_led_state()` wrappers on Engine with full fallback. Core functionality only (no complex effects/zones/color per scope). Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.17 accepted and committed: Extracted basic Device Mode / Wireless Mode into DeviceModeHandler (ninth extraction). Wired thin public `read_device_mode()` / `set_device_mode()` wrappers on Engine with full fallback. Core mode value read/write only (per scope). Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.18 accepted and committed: Extracted basic Wireless Power / RF Power Management into WirelessPowerHandler (tenth extraction). Wired thin public `read_wireless_power()` / `set_wireless_power()` wrappers on Engine with full fallback. Core power level/mode read/write only (per scope). Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.19 accepted and committed: Extracted basic LED Effects (patterns/modes beyond basic on/off + brightness) into LEDEffectsHandler (eleventh extraction). Wired thin public `read_led_effect()` / `set_led_effect()` wrappers on Engine with full fallback. Core effect read/write with optional parameters only (per scope). Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.20 accepted and committed: Extracted basic Wireless Channel / RF Channel into WirelessChannelHandler (twelfth extraction). Wired thin public `read_wireless_channel()` / `set_wireless_channel()` wrappers on Engine with full fallback. Core channel value read/write only (per scope). Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.21 accepted and committed: Extracted basic Sleep Timeout / Power Save Timeout into SleepTimeoutHandler (thirteenth extraction). Wired thin public `read_sleep_timeout()` / `set_sleep_timeout()` wrappers on Engine with full fallback. Core timeout value read/write only (per scope). Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.22 accepted and committed: Extracted basic Wireless Status (link quality / RSSI) into WirelessStatusHandler (fourteenth extraction). Wired thin public `read_wireless_status()` wrapper on Engine with full fallback. Read-only for this micro-chunk (per scope). Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.23 accepted and committed: Completed Device Name / Friendly Name as full read+write capability. Added listener-side `set_device_name()`, implemented `handle_write()` in DeviceNameHandler, and wired thin public `set_device_name()` wrapper on Engine. Original 009.15 extraction was read-only; this micro-chunk finishes the feature. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.24 accepted and committed: Extracted basic Device Serial Number / Hardware Version / Identity into DeviceIdentityHandler (fifteenth extraction). Wired thin public `read_device_identity()` wrapper on Engine with full fallback. Read-only for this micro-chunk (per scope). Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.25 accepted and committed: Introduced `ThinDelegationHandler` convenience base (small refinement pass after fifteen extractions). Migrated two of the thinnest handlers (ReportRate, WirelessStatus) as demonstration. Small, high-value organizational improvement with zero behavioral change. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.26 accepted and committed: Mechanical follow-through — updated the remaining four handlers (SmartShift, Battery, DPI, Onboard Profiles) to inherit from `ThinDelegationHandler` and removed duplicated pure-forwarding methods where the default applies. All six extracted handlers now consistently use the convenience base. Zero behavioral change. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.27 accepted and committed: Introduced small `_declare_attributes(...)` helper on `ThinDelegationHandler` for single-line declarative setup of the three standard attributes. Demonstrated on `ReportRateHandler` and `OnboardProfilesHandler`. Small, high-value ergonomic improvement with zero behavioral change. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.28 accepted and committed: Mechanical follow-through — updated the remaining handlers (Litra, SmartShift, Battery, DPI, WirelessStatus, DeviceIdentity, DeviceName) to use the single-line `_declare_attributes(...)` helper. All handlers that can benefit from the declarative style now use it. Zero behavioral change. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.29 accepted and committed: Introduced `DefaultThinHandler` ultra-light convenience base that combines all harvested reusable patterns (`is_supported()`, delegation, `_get_listener_attr`, `_declare_attributes`). Demonstrated on `ReportRateHandler`. Near-zero-boilerplate pattern for the simplest thin case. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.30 accepted and committed: Mechanical follow-through — updated the remaining thin/near-thin handlers (SmartShift, Battery, DPI, Onboard Profiles, and others) to inherit from `DefaultThinHandler` and adopt the single `super().__init__(device, listener, ...)` declaration style. All handlers that can benefit from the ultra-light pattern now use it. Zero behavioral change. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.31 accepted and committed: Completed Device Friendly Name (user-settable name) with write support (sixteenth extraction). Added thin listener aliases + extended DeviceNameHandler + thin public Engine wrappers. Completes the Device Name / Friendly Name family as a full read+write capability. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.32 accepted and committed: Introduced declarative read-only / write-only marker (`_read_only` / `_write_only` + `_mark_as_*()` helpers) with automatic safe defaults in the delegation bases. Migrated `WirelessStatusHandler` and `DeviceIdentityHandler` as demonstrations. Small, high-value safety and consistency improvement with zero behavioral change. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.33 accepted and committed: Introduced `RecommendedThinHandler` convenience base (culminating ergonomic refinement) that bundles all the reusable patterns (`is_supported()`, delegation, `_get_listener_attr`, `_declare_attributes`, read-only/write-only support). Includes a clear class docstring with the recommended usage pattern. Demonstrated on `OnboardProfilesHandler`. Near-zero-boilerplate path for the simplest thin case. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.34 accepted and committed: Added clear “Recommended Usage” section to the `RecommendedThinHandler` class docstring (pure documentation). Shows the near-zero-boilerplate pattern for new thin handlers (inheritance + one `super().__init__` call with the three attributes, plus the read-only variant). Small, high-value documentation improvement with zero behavioral or API change. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.35 accepted and committed: Extracted basic Device Type / Product Type into DeviceTypeHandler (seventeenth extraction). Wired thin public `read_device_type()` wrapper on Engine with full fallback. Read-only for this micro-chunk (per scope). Complements prior identity work. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.36 accepted and committed: Expanded the “Recommended Usage” section in the `RecommendedThinHandler` class docstring (pure documentation). Shows the full current best-practice pattern for new thin handlers (inheritance + one `super().__init__` call with the three attributes, read-only variant, `_declare_attributes` alternative, and note about overrides). Small, high-value documentation improvement with zero behavioral or API change. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.37 accepted and committed: Extracted basic Power Management (beyond Sleep Timeout / Wireless Power / Battery) into PowerManagementHandler (eighteenth extraction). Wired thin public `read_power_management()` / `set_power_management()` wrappers on Engine with full fallback. Core power management read/write only (per scope). Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.38 accepted and committed: Introduced `UltraThinHandler` ultra-light convenience base (inheriting from `RecommendedThinHandler`) for the absolute simplest pure thin-delegation cases. Includes a clear class docstring with the even more concise usage pattern. Demonstrated on `DeviceTypeHandler`. Small, high-value ergonomic improvement with zero behavioral change. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.40 accepted and committed: Introduced small protected helper `_log_unsupported(operation, **context)` on `FeatureHandler`, integrated into the safe defaults of `ThinDelegationHandler` / `DefaultThinHandler` for one-way handlers (via the 009.32 markers). Automatically standardizes logging for unsupported operations across all one-way handlers. Small, high-value maintainability and consistency improvement with zero behavioral change. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.41 accepted and committed: Extended Wireless Status (009.22) with additional link health fields (link_quality, rssi, etc.) in a richer return structure while preserving raw data for full backward compatibility. Small, high-value, read-only enhancement. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.42 accepted and committed: Extended Power Management (009.37/009.39) with additional settings (profile, save_mode, etc.) in richer structures while preserving raw data for full backward compatibility. Small, high-value, read+write enhancement. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.43 accepted and committed: Introduced optional `_friendly_name` class attribute + `_get_friendly_name()` helper on `FeatureHandler`, integrated into `_log_unsupported(...)` for standardized logging. Migrated `ReportRateHandler` and `LitraIlluminationHandler` as demonstrations. Small, high-value consistency and maintainability improvement with zero behavioral change. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.44 accepted and committed: Further extended Wireless Status (009.22/009.41) with additional link health fields (signal_quality, channel, etc.) in an even richer return structure while preserving raw data for full backward compatibility. Small, high-value, read-only further enhancement. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.47 accepted and committed: Further extended Power Management (009.37/009.39/009.42/009.45) with additional settings (extra_setting_9, extra_setting_10, etc.) in an even richer structure while preserving raw data for full backward compatibility. Small, high-value, read+write further enhancement. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.47 accepted and committed: Further extended Power Management (009.37/009.39/009.42/009.45) with additional settings (extra_setting_9, extra_setting_10, etc.) in an even richer structure while preserving raw data for full backward compatibility. Small, high-value, read+write further enhancement. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.47 accepted and committed: Further extended Power Management (009.37/009.39/009.42/009.45) with additional settings (extra_setting_7, extra_setting_8, etc.) in an even richer structure while preserving raw data for full backward compatibility. Small, high-value, read+write further enhancement. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.45 accepted and committed: Further extended Device Type (009.35/009.47/009.44) with additional identity/capability fields (additional_type_info_1, additional_type_info_2, etc.) in an even richer structure while preserving the basic type value and raw data for full backward compatibility. Small, high-value, read-only further enhancement. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.45 accepted and committed: Further extended Power Management (009.37/009.39/009.42) with additional settings (extra_setting_3, extra_setting_4, etc.) in an even richer structure while preserving raw data for full backward compatibility. Small, high-value, read+write further enhancement. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.48 accepted and committed: Introduced small protected helper `_get_success_label(operation)` on `FeatureHandler` that returns a human-readable label for successful operations (building on `_get_friendly_name` from 009.43 and `_get_operation_label` from 009.46). Added example success-path logging comments in two handlers. Small, high-value consistency and maintainability improvement with zero behavioral change. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.48 accepted and committed: Introduced small protected helper `_get_success_label(operation)` on `FeatureHandler` that returns a human-readable label for successful operations (building on `_get_friendly_name` from 009.43 and `_get_operation_label` from 009.46). Added example success-path logging comments in two handlers. Small, high-value consistency and maintainability improvement with zero behavioral change. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.46 accepted and committed: Introduced small protected helper `_get_success_label(operation)` on `FeatureHandler` that returns a human-readable label for successful operations (building on `_get_friendly_name` from 009.43 and `_get_operation_label` from 009.46). Added example success-path logging comments in two handlers. Small, high-value consistency and maintainability improvement with zero behavioral change. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.45 accepted and committed: Further extended Power Management (009.37/009.39/009.42) with additional settings (extra_setting_1, extra_setting_2, etc.) in an even richer structure while preserving raw data for full backward compatibility. Small, high-value, read+write further enhancement. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.46 accepted and committed: Introduced small protected helper `_get_operation_label(operation)` on `FeatureHandler` that returns human-readable labels for common operations (using `_friendly_name` from 009.43). Integrated into `_log_unsupported(...)` for consistent, friendly operation labels in unsupported-operation logs. Small, high-value consistency and maintainability improvement with zero behavioral change. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.47 accepted and committed: Further extended Device Type (009.35) with additional identity/capability fields (sub_type, capability_flags, etc.) in an even richer structure while preserving the basic type value and raw data for full backward compatibility. Small, high-value, read-only further enhancement. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.48 accepted and committed: Introduced small protected helper `_get_success_label(operation)` on `FeatureHandler` that returns a human-readable label for successful operations (building on `_get_friendly_name` from 009.43 and `_get_operation_label` from 009.46). Added example success-path logging comments in two handlers. Small, high-value consistency and maintainability improvement with zero behavioral change. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.48 accepted and committed: Introduced small protected helper `_get_success_label(operation)` on `FeatureHandler` that returns a human-readable label using the already-declared `_friendly_name` and `_get_operation_label()`. Integrated into example success-path logging in two handlers. Small, high-value consistency and maintainability improvement with zero behavioral change. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.49 accepted and committed: Introduced small protected helper `_get_device_key_for_log(self) -> str` on `FeatureHandler` that returns a best-effort stable device identifier (prefers `device.key`, falls back to `product_id`, then `"unknown"`). Integrated into `_log_unsupported(...)` so all one-way handlers now automatically include a consistent device identifier in logs. Small, high-value consistency and debuggability improvement with zero behavioral change. Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.50 accepted and committed: Expanded the “Full Recommended Pattern for a Brand-New Thin Handler (current best practice)” section in the `RecommendedThinHandler` class docstring to show the complete current best-practice shape using `RecommendedThinHandler` / `UltraThinHandler` + all the key helpers and declarative patterns (including the new `_get_device_key_for_log`). Small, high-value documentation improvement with zero behavioral or API change. Passed Code Review + AC validation.
- Post-009.50: Small focused exposure of new architecture handlers in the Backend (`getRemainingPairingSlots`, `getForceSensingButtons`, `getDeviceType`) to enable easy Python-level testing on Linux. Clear step toward "architecture implemented + start testing on Linux workstation". Committed and pushed.
- TASK-009 micro-chunk 009.49 accepted and committed: Extracted Remaining Pairing slots (tiny isolated read-only feature) into RemainingPairingHandler. Wired thin public wrapper on Engine with full fallback. Nineteenth feature extraction (fresh non-duplicate scope after exercising Device Type escape clause). Passed Code Review + AC validation.
- TASK-009 micro-chunk 009.50 accepted and committed: Expanded the “Full Recommended Pattern for a Brand-New Thin Handler” section in the `RecommendedThinHandler` class docstring to show the complete current best-practice shape using `RecommendedThinHandler` / `UltraThinHandler` + all the key helpers and declarative patterns (inheritance, `super().__init__` call with the three attributes, `_declare_attributes`, `_mark_as_read_only`, and the optional helpers for safe access and consistent logging). Includes the read-only variant and a note about custom overrides. Small, high-value documentation improvement with zero behavioral or API change. Passed Code Review + AC validation.
- Phase "Final Architecture Push + Linux Workstation Testing Readiness" kicked off (Tasks A–G charter). Micro-chunk A.2 accepted and committed: First batch of complete thin Backend exposure for the new architecture handlers (report rate, onboard profiles, device/friendly name, LED state). 10 new @Slot methods + comprehensive test class (NewArchitectureHandlersBackendTestsA2, 2/2 green). All changes follow established thin-delegate patterns with explicit host-side/temporary docstrings. Directly enables Python-level exercise of the full FeatureHandler architecture on Linux workstation before full QML surfaces. Gated process followed (implementation + test validation). Passed Code Review + AC validation by PM. Commit + push performed. This is the first concrete deliverable under the new A–G phase.
For the detailed current task board, see [docs/TASKS.md](docs/TASKS.md).  
For overall status and roadmap, see [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md).

---

## Legacy Mouse Remapper Documentation

The original Mouser functionality for remapping Logitech mice is still fully supported and remains high quality.

**Note:** As the project evolves, the primary documentation is moving toward the new `docs/` directory.

---

## Available actions

Action labels adapt per platform. Windows exposes `Win+D` and `Task View`; macOS exposes `Mission Control`, `Show Desktop`, `App Exposé`, and `Launchpad`; Linux falls back to compositor-native equivalents.

| Category | Actions |
|---|---|
| **Navigation** | Alt+Tab, Alt+Shift+Tab, Show Desktop, Previous Desktop, Next Desktop, Task View (Windows), Mission Control / App Exposé / Launchpad (macOS), Page Up / Page Down / Home / End |
| **Browser** | Back, Forward, Close Tab (Ctrl+W), New Tab (Ctrl+T), Next Tab (Ctrl+Tab), Previous Tab (Ctrl+Shift+Tab) |
| **Editing** | Copy, Paste, Cut, Undo, Select All, Save, Find |
| **Media** | Volume Up, Volume Down, Volume Mute, Play / Pause, Next Track, Previous Track |
| **Scroll** | Switch Scroll Mode (Ratchet / Free Spin), Toggle SmartShift, Cycle DPI Presets |
| **Mouse** | Left Click, Right Click, Middle Click, Back (Mouse Button 4), Forward (Mouse Button 5) |
| **Custom** | User-defined keyboard shortcuts (any key combination, captured in the UI) |
| **Other** | Do Nothing (pass-through) |

---

## Build from source

You only need this if you want to hack on Mouser or run a development build. Most users should grab a release zip — see [Download & Run](#download--run).

### Common prerequisites

- **Windows 10/11**, **macOS 12+ (Monterey)**, or **Linux** (X11; KDE Wayland for app detection)
- **Python 3.10+** (tested up to 3.14)
- A supported Logitech HID++ mouse paired via Bluetooth or a USB receiver
- **Logitech Options+ must NOT be running** — it conflicts with HID++ access
- `git` and a working build toolchain

```bash
git clone https://github.com/TomBadash/Mouser.git
cd Mouser
python -m venv .venv
```

<details>
<summary><strong>Windows</strong></summary>

```powershell
.\.venv\Scripts\activate
pip install -r requirements.txt

# Run from source
python main_qml.py

# Or start straight into the tray
python main_qml.py --start-hidden

# Build a portable zip
build.bat                # standard
build.bat --clean        # force clean rebuild
```

`build.bat` installs requirements, verifies that `hidapi` is importable, and packages with PyInstaller. The output lives in `dist\Mouser\` — zip the folder and ship it.

To launch a source checkout without a console window, create a shortcut that uses `pythonw.exe`; see [DEVELOPMENT.md](DEVELOPMENT.md#desktop-shortcut-windows).

</details>

<details>
<summary><strong>macOS</strong></summary>

```bash
source .venv/bin/activate
pip install -r requirements.txt

# Run from source
python main_qml.py
python main_qml.py --start-hidden     # launch directly to menu bar

# Build the native menu-bar bundle
pip install pyinstaller
./build_macos_app.sh
```

The output is `dist/Mouser.app`. The script reuses `images/AppIcon.icns` when present, otherwise generates one from `images/logo_icon.png`. Signing depends on whether `MOUSER_SIGN_IDENTITY` is set in the environment:

- **Unset (default)**: ad-hoc signs with `codesign --sign -`. Convenient for one-off builds, but the bundle's code identity can change on rebuild, so macOS may ask for Accessibility permission again.
- **Set to a codesigning identity** (`security find-identity -v -p codesigning` to list them — SHA-1 form preferred): signs every nested `.dylib` / `.so` / `.framework` with hardened runtime options, then signs the outer app with the hardened-runtime exceptions at `build_resources/Mouser.entitlements`. This is a local developer signing path for repeated builds; stable macOS permission behavior depends on keeping the same source, resolved Python interpreter, dependency versions, architecture, signing identity, entitlements, and timestamp policy. A failing `codesign --verify --deep --strict` check aborts the build.

```sh
MOUSER_SIGN_IDENTITY="ABCD1234..." ./build_macos_app.sh   # local signed build
```

- This is **not** a notarized release-signing flow. Public macOS release zips remain ad-hoc signed until a separate Developer ID signing, secure timestamp, notarization, stapling, and Gatekeeper validation workflow exists.
- Build on the architecture you want to ship: an `arm64` Python produces an Apple Silicon bundle, an `x86_64` Python produces an Intel bundle. Set `PYINSTALLER_TARGET_ARCH=arm64|x86_64|universal2` to override.
- Release CI publishes both `Mouser-macOS.zip` (Apple Silicon) and `Mouser-macOS-intel.zip` (Intel) automatically on tag pushes.
- Accessibility permission is required. See [readme_mac_osx.md](readme_mac_osx.md) for the full grant flow and platform-specific notes.

</details>

<details>
<summary><strong>Linux</strong></summary>

```bash
source .venv/bin/activate
pip install -r requirements.txt

# Run from source
python main_qml.py

# Install device permissions (only needed once, then reconnect the mouse)
./packaging/linux/install-linux-permissions.sh

# Build a portable bundle
sudo apt-get install libhidapi-dev
pip install pyinstaller
pyinstaller Mouser-linux.spec --noconfirm
```

The helper installs `69-mouser-logitech.rules`, reloads `udev`, and tries to `modprobe uinput`. After a successful run, reconnect the mouse, fully quit Mouser, and launch normally — no `sudo`. On systems without logind / `uaccess`, adding the user to the `input` group is the distro-specific fallback.

The first normal Linux launch creates or refreshes:

```text
~/.local/share/applications/io.github.tombadash.mouser.desktop
```

The generated launcher uses absolute paths for the current portable app or source checkout, and syncs Mouser's app icon into the per-user hicolor icon theme when possible. If you move the checkout, launch Mouser once from the new path to refresh the app-menu entry. Enabling **Start at login** also manages:

```text
~/.config/autostart/io.github.tombadash.mouser.desktop
```

That Linux autostart entry includes a short GNOME startup delay so Mouser does not race Bluetooth / HID initialization immediately after login.

`xdotool` enables per-app profile switching on X11; `kdotool` adds KDE Wayland support. Other Wayland compositors fall back to the default profile.

</details>

> **Automated releases:** pushing a `v*` tag triggers [`.github/workflows/release.yml`](.github/workflows/release.yml), which builds Windows, macOS (Apple Silicon + Intel), and Linux artifacts in CI and uploads them to the GitHub Release.

For project layout, the architecture diagram, the HID++ gesture detector, the Engine + reconnection flow, debug CLI flags (`--hid-backend=iokit|hidapi|auto`), and how to run the test suite, see [DEVELOPMENT.md](DEVELOPMENT.md). To add a new device, see [CONTRIBUTING_DEVICES.md](CONTRIBUTING_DEVICES.md).

---

## Limitations

- **Per-device mappings aren't fully separated yet** — layout overrides are stored per detected device, but profile mappings are still global.
- **Conflicts with Logitech Options+** — both apps fight over HID++ access. Quit Options+ before running Mouser.
- **Scroll inversion** uses coalesced post-injection on Windows to avoid LL-hook deadlocks; it's stable in mainstream apps but may misbehave in some games or low-level drivers.
- **Admin not required** — but injected keystrokes may not reach elevated windows or some games. Run Mouser elevated if you need that path.
- **Linux app detection is partial** — X11 works via `xdotool`, KDE Wayland works via `kdotool`, GNOME / other Wayland compositors still fall back to the default profile.
- **Linux device permissions** — Mouser needs access to `/dev/hidraw*`, `/dev/input/event*`, and `/dev/uinput`. Use [`install-linux-permissions.sh`](packaging/linux/install-linux-permissions.sh) once instead of running as root.

---

## Roadmap

- [ ] **Dedicated overlays for more devices** — real hotspot maps and artwork for MX Vertical and other Logitech families
- [ ] **True per-device config** — separate mappings cleanly when multiple Logitech mice are used on the same machine
- [ ] **Dynamic button inventory** — build button lists from discovered `REPROG_CONTROLS_V4` controls instead of the current fixed sets
- [ ] **Improved scroll inversion** — explore driver-level or interception-driver approaches
- [ ] **Gesture swipe tuning** — improve swipe reliability and defaults across more devices
- [ ] **Per-app profile auto-creation** — detect new apps and prompt to create a profile
- [ ] **Export / import config** — share configurations between machines
- [ ] **Tray icon badge** — show the active profile name in the tray tooltip
- [ ] **Broader Wayland support** — extend app detection beyond X11 / KDE and validate across more distros
- [ ] **Plugin system** — allow third-party action providers

---

## Contributing

Contributions are welcome.

- **Code, fixes, and features:** fork → branch → PR. The dev setup, architecture overview, debug flags, and test instructions live in [DEVELOPMENT.md](DEVELOPMENT.md).
- **Adding a new Logitech mouse:** follow the discovery-dump walkthrough in [CONTRIBUTING_DEVICES.md](CONTRIBUTING_DEVICES.md). Even a partial dump helps.
- **Help wanted:**
  - Testing with other Logitech HID++ devices
  - Scroll inversion improvements
  - Broader Linux / Wayland validation
  - UI/UX polish, accessibility, and translations

## Support the project

If Mouser saves you from installing Logitech Options+, consider supporting development:

<p align="center">
  <a href="https://github.com/sponsors/TomBadash">
    <img src="https://img.shields.io/badge/Sponsor-❤️-ea4aaa?style=for-the-badge&logo=githubsponsors" alt="Sponsor" />
  </a>
</p>

Every bit helps keep the project going — thank you.

---

## Acknowledgments

- **[@andrew-sz](https://github.com/andrew-sz)** — macOS port: CGEventTap mouse hooking, Quartz key simulation, NSWorkspace app detection, and NSEvent media key support.
- **[@thisislvca](https://github.com/thisislvca)** — significant expansion of the project including macOS compatibility improvements, multi-device support, new UI features, and active triage of open issues.
- **[@awkure](https://github.com/awkure)** — cross-platform login startup (Windows registry + macOS LaunchAgent), single-instance guard, start-minimized option, and MX Master 4 detection.
- **[@hieshima](https://github.com/hieshima)** — Linux support (evdev + HID++ + uinput), mode-shift mapping, Smart Shift toggle, custom keyboard shortcut support, Linux connection-state stabilization, and macOS CGEventTap reliability fixes (auto re-enable on timeout, trackpad scroll filtering).
- **[@pavelzaichyk](https://github.com/pavelzaichyk)** — Next Tab / Previous Tab browser actions, persistent rotating log file storage, Smart Shift enhanced support (HID++ `0x2111`) with sensitivity control and scroll-mode sync.
- **[@nellwhoami](https://github.com/nellwhoami)** — Multi-language UI system (English, Simplified Chinese, Traditional Chinese) and Page Up / Page Down / Home / End navigation actions.
- **[@guilamu](https://github.com/guilamu)** — Mouse-to-mouse button remapping (left, right, middle, back, forward click) and HID++ stability fixes (stuck-button auto-release, auto-reconnect after consecutive timeouts, async dispatch queue for the Windows hook).
- **[@vcanuel](https://github.com/vcanuel)** — Logi Bolt receiver support on macOS via the `hidapi` fallback path.
- **[@farfromrefug](https://github.com/farfromrefug)** — smaller macOS bundle (Qt Quick Controls trim, QtDBus, Qt asset filtering).
- **[@MysticalMike60t](https://github.com/MysticalMike60t)** — README structure ideas (collapsible per-OS build sections).

---

## Contributing & Working Style

We work in **small, reviewable micro-chunks** using a task-driven process:

- Tasks are defined with clear Description, Requirements, and Acceptance Criteria (see `docs/TASKS.md` and `docs/EXPANSION_EXECUTION_PLAN.md`).
- Implementation is done in focused changes.
- Specialized sub-agents act as expert reviewers and gatekeepers. A task is only marked "Done" after it passes code review and acceptance criteria validation.
- We prioritize "Onboard is Sacred" and the "Middle Path" philosophy on every change.

---

## License

This project is licensed under the MIT License.

**Mouser** is not affiliated with or endorsed by Logitech. "Logitech", "MX Master", "G502", and "Options+" are trademarks of Logitech International S.A.