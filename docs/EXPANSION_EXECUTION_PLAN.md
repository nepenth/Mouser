# Mouser Expansion Execution Plan

**Created:** 2026-06-19  
**Orchestrator:** Master execution loop for completing partial work, upstream sync, and expansion goals.  
**Source of truth for:** task IDs, requirements, acceptance criteria, dependencies, and progress dashboard.

---

## Executive Overview

This plan integrates:
- Section **D** (Multi-Device / Expansion Features) partial items from the Executive Codebase Report
- Section **E** (Backend API Exposure — Task A)
- All explicit **TODO** comments, **placeholder** feature IDs, and **skeleton** implementations
- **P0/P1/P2** prioritized next steps and strategic advice from the report
- **Upstream sync** from `TomBadash/Mouser` (G502 family, screenshots, UI/a11y, CI fixes)

**Execution model:** One work item at a time → implement → self-review → orchestrator review → commit → push → update dashboard.

---

## Progress Dashboard

| Phase | Items | Done | Status |
|-------|-------|------|--------|
| 0 — Foundation & Sync | 5 | 0 | **IN PROGRESS** |
| 1 — Test & Code Health (P0) | 4 | 0 | Pending |
| 2 — Task A: Backend Exposure | 3 | 0 | Pending |
| 3 — Upstream Feature Integration | 4 | 0 | Pending |
| 4 — Section D Completion | 8 | 0 | Pending |
| 5 — Placeholders & Architecture | 6 | 0 | Pending |
| 6 — High-Risk Expansion | 5 | 0 | Pending |
| 7 — Tasks F–G (Linux & Docs) | 3 | 0 | Pending |
| **TOTAL** | **38** | **0** | **0%** |

---

## Phase 0 — Foundation & Sync

### 0.1 — Merge Upstream `TomBadash/Mouser` master

| Field | Value |
|-------|-------|
| **Priority** | P0 (blocker) |
| **Complexity** | L (large — 27 upstream / 169 fork commits since merge-base `44880fb`) |
| **Dependencies** | None |

**Requirements**
- Add `upstream` remote → `https://github.com/TomBadash/Mouser.git` if missing.
- Merge `upstream/master` into `master` preserving all fork expansion work (keyboard, Litra, FeatureHandlers, Backend A.2).
- Resolve conflicts favoring: upstream for G502 catalog/layouts, screenshots, a11y, hide-to-tray; fork for `core/devices/`, keyboard middle-path, Litra, `docs/TASKS.md` expansion tracking.
- Full test suite runs after merge; record baseline pass/fail count.

**Acceptance Criteria**
- `git merge-base master upstream/master` shows merge completed (single history).
- G502 family entries from upstream present (`g502`, `g502_hero`, `g502_lightspeed`, `g502_x` layouts in catalog).
- Fork-only directories intact: `core/devices/`, `ui/qml/KeyboardPage.qml`, `LitraControls.qml`, `docs/EXPANSION_EXECUTION_PLAN.md`.
- `python -m unittest discover -s tests` completes (failures documented if pre-existing).
- Commit message: `merge: integrate upstream TomBadash/Mouser master (G502, screenshots, a11y)`.

---

### 0.2 — Reconcile G502 Device Support Post-Merge

| Field | Value |
|-------|-------|
| **Priority** | P0 |
| **Complexity** | M |
| **Dependencies** | 0.1 |

**Requirements**
- Remove duplicate/conflicting `g502_x_lightspeed` fork catalog entry if upstream supersedes it.
- Ensure G502 X Lightspeed PIDs (`0xC547`, `0x409F`, `0xC098`, Plus variants) resolve to dedicated `g502` UI layout.
- Verify `classify_device_kind` still classifies G502 as `mouse` with onboard + HIRES_WHEEL features.
- Add/adjust tests in `test_logi_devices.py` / `test_device_layouts.py` for G502 layout selection.

**Acceptance Criteria**
- `build_connected_device_info` for G502 X returns `ui_layout` key `g502` (not `generic_mouse`).
- Layout dropdown in MousePage lists G502 layout as selectable (upstream behavior).
- No regression in MX Master / Anywhere layout resolution.
- Relevant device tests pass.

---

### 0.3 — Documentation Hygiene

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Complexity** | S |
| **Dependencies** | 0.1 |

**Requirements**
- Update `docs/TASKS.md`: mark TASK-004–009, 005–008 as **Done** where README work log confirms completion.
- Remove stale `ui/backend.py` comment ("future KeyboardPage").
- Fix `core/devices/device_name_handler.py` docstring (write is implemented).
- Deduplicate README Completed Work Log duplicate TASK-009 entries (single entry per micro-chunk).

**Acceptance Criteria**
- No task marked Backlog that has "accepted and committed" implementation notes without an open AC gap.
- Grep for `future KeyboardPage` in `backend.py` returns zero matches.
- `device_name_handler.py` docstring reflects read+write capability.

---

### 0.4 — Consolidate `logi_device.py` Duplicate Methods

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Complexity** | S |
| **Dependencies** | 0.1 |

**Requirements**
- Remove 6 duplicate `_get_success_label()` definitions in `FeatureHandler` (keep exactly one).
- Run full test suite; zero behavioral change.

**Acceptance Criteria**
- Exactly one `_get_success_label` method body in `core/logi_device.py`.
- All tests pass.

---

### 0.5 — CI Alignment with Upstream

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Complexity** | S |
| **Dependencies** | 0.1 |

**Requirements**
- Merge upstream `.github/workflows/ci.yml` changes (Qt runtime libs, signing guard tests if present).
- Ensure CI steps: compile, unittest, qmllint all run on push.

**Acceptance Criteria**
- Local CI-equivalent commands pass: `py_compile`, `unittest discover`, qmllint.
- Workflow file has no unresolved merge conflict markers.

---

## Phase 1 — Test & Code Health (P0)

### 1.1 — Fix SmartShift `_delegate_or_fallback` Regression

| Field | Value |
|-------|-------|
| **Priority** | P0 |
| **Complexity** | S |
| **Dependencies** | 0.1 |

**Requirements**
- Fix `Engine.set_smart_shift` so `_fallback` accepts `*args` OR `_delegate_or_fallback` does not pass write args to zero-arg fallbacks.
- Apply same pattern audit to `read_smart_shift` and other `_delegate_or_fallback` call sites.

**Acceptance Criteria**
- `tests/test_smart_shift.py` — all `EngineSmartShiftTests` pass (3 previously errored).
- No new failures in full suite.

---

### 1.2 — Fix FN Inversion Pending State Clear

| Field | Value |
|-------|-------|
| **Priority** | P0 |
| **Complexity** | S |
| **Dependencies** | 0.1 |

**Requirements**
- `_apply_pending_set_fn_inversion` must clear `_pending_fn` to `None` on successful apply (mirror backlight behavior).

**Acceptance Criteria**
- `test_apply_pending_set_fn_inversion` passes.
- `MXMechanicalMiniMiddlePathTests` class: 100% pass.

---

### 1.3 — Keyboard `_try_connect` Integration Test (TODO)

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Complexity** | M |
| **Dependencies** | 1.2 |

**Requirements**
- Implement test described in `tests/test_hid_gesture.py` TODO (lines 958–963).
- Mock `_vendor_hid_infos` + light `_find_feature` peek; assert keyboard early-return, no REPROG work, correct `device_kind`.

**Acceptance Criteria**
- New test method in `MXMechanicalMiniMiddlePathTests` or dedicated class.
- Test passes; TODO comment removed or replaced with reference to test name.

---

### 1.4 — Full Suite Green Gate

| Field | Value |
|-------|-------|
| **Priority** | P0 |
| **Complexity** | S |
| **Dependencies** | 1.1, 1.2 |

**Requirements**
- `python -m unittest discover -s tests` → 0 failures, 0 errors (skipped allowed).

**Acceptance Criteria**
- CI unittest step would pass on clean checkout.

---

## Phase 2 — Task A: Complete Backend API Exposure

### 2.1 — Backend Batch B: Device Mode, Wireless, Sleep

| Field | Value |
|-------|-------|
| **Priority** | P0 |
| **Complexity** | M |
| **Dependencies** | 1.4 |

**Requirements**
- Add thin `@Slot` methods in `ui/backend.py`:
  - `readDeviceMode` / `setDeviceMode`
  - `readWirelessPower` / `setWirelessPower`
  - `readWirelessChannel` / `setWirelessChannel`
  - `readSleepTimeout` / `setSleepTimeout`
  - `readWirelessStatus`
- Pattern: `hasattr` guard, safe defaults, "host-side only, temporary" docstrings.
- Add `NewArchitectureHandlersBackendTestsB` in `tests/test_backend.py`.

**Acceptance Criteria**
- All 9 methods callable from Python with no engine → safe defaults.
- With mock engine → correct delegation.
- New test class: ≥2 tests per method group (no-engine + delegation), all green.

---

### 2.2 — Backend Batch C: LED Effects, Identity, Power Management

| Field | Value |
|-------|-------|
| **Priority** | P0 |
| **Complexity** | M |
| **Dependencies** | 2.1 |

**Requirements**
- Add slots: `readLedEffect` / `setLedEffect`, `readDeviceIdentity`, `readPowerManagement` / `setPowerManagement`.
- Tests: `NewArchitectureHandlersBackendTestsC`.

**Acceptance Criteria**
- Every remaining Engine public method from TASK-009 extractions has a Backend `@Slot`.
- Matrix verified: Engine method list vs Backend slot list = 0 gaps.
- All new tests pass.

---

### 2.3 — Task A Closure Audit

| Field | Value |
|-------|-------|
| **Priority** | P0 |
| **Complexity** | S |
| **Dependencies** | 2.2 |

**Requirements**
- Script or documented checklist mapping `Engine.read_*` / `set_*` / `get_*` → `Backend` slots.
- Update `docs/TASKS.md` Task A → **Done**.

**Acceptance Criteria**
- Checklist shows 100% coverage.
- `tests/test_backend.py` has coverage for every new slot (no-engine path minimum).

---

## Phase 3 — Upstream Feature Integration

### 3.1 — Screenshot Actions (from upstream)

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Complexity** | M |
| **Dependencies** | 0.1 |

**Requirements**
- Ensure merged screenshot action backends present: Windows native, GNOME portal, KDE Spectacle, robust KDE backend.
- Screenshot actions available in button remapping UI.
- Screenshot save location settings wired.

**Acceptance Criteria**
- `key_registry` / action list includes screenshot actions.
- Tests from upstream for screenshot backends pass.
- Linux setting-open remapping fix (`keep Linux remapping active with settings open`) preserved.

---

### 3.2 — UI/A11y/Tray Improvements (from upstream)

| Field | Value |
|-------|-------|
| **Priority** | P2 |
| **Complexity** | S |
| **Dependencies** | 0.1 |

**Requirements**
- Hide-to-tray shortcuts (Cmd-W/Cmd-M/Esc) integrated without breaking fork Keyboard/Litra pages.
- Accessible roles + localized labels from upstream preserved.
- App icon refresh pipeline aligned.

**Acceptance Criteria**
- qmllint passes.
- No hardcoded English strings added by merge in Keyboard/Litra QML.

---

### 3.3 — TASK-003 Polish Batch

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Complexity** | M |
| **Dependencies** | 1.4 |

**Requirements**
- Align keyboard feature response parsing with rest of `hid_gesture.py`.
- Document or fix `set_*` vs `read_*` timeout asymmetry (vs DPI).

**Acceptance Criteria**
- Senior-review checklist in TASK-003 items addressed or documented with justification in code comments.
- No new test failures.

---

### 3.4 — Linux Remapping + Permissions Validation

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Complexity** | S |
| **Dependencies** | 0.1, 0.2 |

**Requirements**
- Verify `packaging/linux/69-mouser-logitech.rules` covers G502 + keyboard Bolt receiver PIDs post-merge.
- Document any new PIDs from upstream G502 Plus ids.

**Acceptance Criteria**
- udev rules file includes all G502 product IDs from catalog.
- `test_linux_permissions.py` passes.

---

## Phase 4 — Section D Completion (Expansion Features)

### 4.1 — Multi-Receiver: Complete Candidate Ordering & Logging

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Complexity** | M |
| **Dependencies** | 0.2, 1.4 |
| **Status was** | Partially Implemented |

**Requirements**
- Audit `_try_connect` / discovery for simultaneous Bolt + Lightspeed; G502 wins for mouse control when both present.
- Structured log lines per device candidate with `device_kind`, receiver type, feature summary.
- Test: mock multi-receiver discovery ordering.

**Acceptance Criteria**
- Test demonstrates G502 preferred over keyboard for active mouse connection when configured.
- No gesture diversion attempted on keyboard candidate (existing short-circuit test + new integration test).

---

### 4.2 — Litra Beam: Real Feature ID & Handler Validation

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Complexity** | M |
| **Dependencies** | 2.2 |
| **Status was** | Partially Implemented (placeholder `0x1A00`) |

**Requirements**
- Research correct HID++ feature ID for Litra Beam illumination (Solaar DB, Logitech docs, upstream if added).
- Replace `FEAT_LITRA_ILLUMINATION` placeholder constant.
- If ID unknown without hardware: implement runtime-only discovery (feature name scan) with constant as fallback; document in code.
- Add `hasLitraIlluminationSupported` Backend property (not just name heuristic `hasLitraBeam`).

**Acceptance Criteria**
- No comment saying "Placeholder — replace" for Litra feature ID unless accompanied by runtime discovery path.
- Unit test: Litra classification + illumination index detection with mocked feature list.
- `LitraControls.qml` binds to capability property, not display-name heuristic alone.

---

### 4.3 — Litra Dedicated Page (not footer-only)

| Field | Value |
|-------|-------|
| **Priority** | P2 |
| **Complexity** | M |
| **Dependencies** | 4.2 |

**Requirements**
- Add sidebar nav entry or sub-section for Lights/Devices.
- Move `LitraControls` into dedicated page; footer card hidden when on dedicated page (mirror Keyboard pattern).

**Acceptance Criteria**
- User can navigate to Litra page when `hasLitraIlluminationSupported` true.
- No duplicate Litra controls visible on same page.

---

### 4.4 — Keyboard Host-Side Settings Replay on Reconnect

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Complexity** | M |
| **Dependencies** | 1.4 |
| **Status was** | Planned |

**Requirements**
- On HID++ reconnect, replay pending backlight + FN inversion if per-device `allow_host_*` true (mirror SmartShift replay).
- Log replay actions clearly.

**Acceptance Criteria**
- Unit test: reconnect triggers `set_backlight` / `set_fn_inversion` when flags enabled.
- Documented as host-side temporary in logs.

---

### 4.5 — Extract BacklightHandler & FnInversionHandler

| Field | Value |
|-------|-------|
| **Priority** | P2 |
| **Complexity** | L |
| **Dependencies** | 2.3, 4.4 |

**Requirements**
- Create `core/devices/backlight_handler.py` and `fn_inversion_handler.py`.
- Wire Engine delegation; remove direct listener calls from Engine for these features.
- 100% backward compatible public API.

**Acceptance Criteria**
- Handlers use `RecommendedThinHandler` pattern.
- `test_hid_gesture.py` keyboard tests still pass.
- Engine `read_backlight` / `set_backlight` / `read_fn_inversion` / `set_fn_inversion` delegate to handlers.

---

### 4.6 — Multi-Device UI Phase 1 (Sidebar Device List)

| Field | Value |
|-------|-------|
| **Priority** | P1 (High Risk) |
| **Complexity** | XL |
| **Dependencies** | 4.1, 2.3 |

**Requirements**
- Backend exposes `connectedDevices` list (all discovered HID++ devices, not just active mouse).
- Sidebar or header shows device entries with name, kind icon, battery, connection state.
- Selecting device switches context for Keyboard vs Mouse vs Litra pages.
- Active mouse hook still targets one mouse; keyboard/Litra controls target selected device.

**Acceptance Criteria**
- With mocked 2 devices (G502 + MX Mechanical Mini), UI lists both.
- Selecting keyboard shows KeyboardPage controls for keyboard device regardless of active mouse.
- Design doc Phase 1 AC met (visibility + appropriate page routing).
- No mouse remapping regression (full test suite green).

---

### 4.7 — FeatureHandler: Runtime Feature Discovery for Placeholder IDs

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Complexity** | L |
| **Dependencies** | 2.3 |

**Requirements**
- For each `FEAT_*` marked placeholder in `hid_gesture.py`, either:
  - (a) Replace with verified HID++ ID from Logitech/Solaar reference, OR
  - (b) Mark as `FEAT_OPTIONAL_*` with discovery via full feature table walk only (no hardcoded wrong ID probing).
- Document feature ID source in comment (Solaar link / device dump / spec).

**Acceptance Criteria**
- Grep `Placeholder` in `hid_gesture.py` → zero matches OR each match has `SOURCE:` comment and discovery strategy.
- Handlers' `is_supported()` returns False when feature not in device table (no false positives from wrong IDs).

---

### 4.8 — G502 X Onboard Profile UX

| Field | Value |
|-------|-------|
| **Priority** | P2 |
| **Complexity** | M |
| **Dependencies** | 0.2, 2.2 |

**Requirements**
- ScrollPage or MousePage section for onboard profile display/switch when `read_onboard_profile` supported.
- Use existing Backend `readOnboardProfile` / `switchOnboardProfile`.

**Acceptance Criteria**
- When G502 connected (mock), UI shows onboard profile controls.
- Switch calls Backend slot; success/failure feedback shown.

---

## Phase 5 — Architecture & Placeholders

### 5.1 — `LogitechDevice` Subclasses (Mouse/Keyboard/Other)

| Field | Value |
|-------|-------|
| **Priority** | P2 |
| **Complexity** | L |
| **Dependencies** | 4.5, 4.6 |

**Requirements**
- Implement `MouseDevice`, `KeyboardDevice`, `OtherDevice` per design doc.
- Factory from `classify_device_kind` + capability inventory.

**Acceptance Criteria**
- Device attachment uses subclass type.
- Existing tests pass; new test for factory classification.

---

### 5.2 — Incremental `hid_gesture.py` Decomposition Plan Execution (Pass 1)

| Field | Value |
|-------|-------|
| **Priority** | P2 (High Risk) |
| **Complexity** | XL |
| **Dependencies** | 4.5, 4.7 |

**Requirements**
- Extract device discovery into `core/hid_discovery.py` (~400 lines).
- Extract feature constants into `core/hid_features.py`.
- `hid_gesture.py` imports from new modules; no behavior change.

**Acceptance Criteria**
- `hid_gesture.py` reduced by ≥300 lines.
- All hid_gesture tests pass without modification (or with import-only changes).

---

### 5.3 — Force Sensing Button Backend + Test

| Field | Value |
|-------|-------|
| **Priority** | P2 |
| **Complexity** | S |
| **Dependencies** | 2.2 |

**Requirements**
- Verify `getForceSensingButtons` Backend slot has tests (may exist from post-009.50).
- Add if missing.

**Acceptance Criteria**
- `test_backend.py` covers force sensing no-engine + delegation.

---

### 5.4 — Battery Handler: Remove Placeholder Parse Helper

| Field | Value |
|-------|-------|
| **Priority** | P2 |
| **Complexity** | S |
| **Dependencies** | 4.7 |

**Requirements**
- Complete battery parse in listener or handler (TASK-009 note: "minimal placeholder parse helper").

**Acceptance Criteria**
- No "placeholder parse" comment in battery path.
- `test_hid_gesture` / battery tests pass.

---

### 5.5 — Per-Device KVM Preset (Design Phase 4)

| Field | Value |
|-------|-------|
| **Priority** | P3 |
| **Complexity** | M |
| **Dependencies** | 4.6 |

**Requirements**
- Config preset `kvm_mode` defaults: no grab, controls-only, allow_host_backlight true, diversion false.
- UI toggle on Settings/Keyboard page.

**Acceptance Criteria**
- Applying preset updates per-device `keyboard_middle_path` flags.
- Documented in config schema comment.

---

### 5.6 — Webcam Features Stub Removal or Explicit Deferral

| Field | Value |
|-------|-------|
| **Priority** | P3 |
| **Complexity** | S |
| **Dependencies** | None |

**Requirements**
- PROJECT_PLAN lists webcam as "very low priority."
- Either remove any webcam stubs OR add `docs/DEFERRED.md` entry with explicit out-of-scope statement.

**Acceptance Criteria**
- No ambiguous webcam placeholder code in `core/`.
- Deferred scope documented.

---

## Phase 6 — High-Risk Expansion

### 6.1 — Multi-Device State Model Refactor

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Complexity** | XL |
| **Dependencies** | 4.6 |

**Requirements**
- Replace single `connected_device` with `active_mouse_device` + `selected_device` + `all_devices[]` in Engine/Backend.
- Migration path for existing Backend properties.

**Acceptance Criteria**
- Mouse remapping uses `active_mouse_device`.
- Keyboard/Litra APIs use `selected_device`.
- All 511+ tests pass; new multi-device tests added.

---

### 6.2 — Safe Selective Diversion: Linux evdev Validation

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Complexity** | M |
| **Dependencies** | 4.6, Task D from charter |

**Requirements**
- Document + test diversion path on Linux (mock evdev + HID++ divert).
- Task 007 closure: end-to-end from opt-in toggle → CID divert → mappable event.

**Acceptance Criteria**
- Integration test covers diversion gated by `allow_diversion_backlight`.
- TASK-007 marked Done in TASKS.md.

---

### 6.3 — Broader Keyboard Diversion (Media Keys) — Optional Opt-In

| Field | Value |
|-------|-------|
| **Priority** | P3 |
| **Complexity** | L |
| **Dependencies** | 6.2 |

**Requirements**
- Per design doc Phase 2: optional Volume/Mute/Search CIDs behind per-key opt-in (not just backlight).
- Config: `allow_diversion_media` etc.

**Acceptance Criteria**
- Default off; when enabled, only listed CIDs diverted.
- UI warning present.

---

### 6.4 — Engine Size Reduction (Handler Attachment Generator)

| Field | Value |
|-------|-------|
| **Priority** | P2 |
| **Complexity** | M |
| **Dependencies** | 5.2 |

**Requirements**
- Replace 15+ `_maybe_attach_*_handler` methods with declarative registry dict.

**Acceptance Criteria**
- `engine.py` attachment block reduced by ≥200 lines.
- Zero behavior change (tests pass).

---

### 6.5 — Final Architecture Push Closure (TASK-009)

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Complexity** | M |
| **Dependencies** | 4.5, 5.1, 2.3 |

**Requirements**
- Mark TASK-009 Done with evidence: ≥19 handlers, consistent delegation, documentation in `RecommendedThinHandler` docstring current.

**Acceptance Criteria**
- TASK-009 status Done in TASKS.md.
- All handlers inherit from appropriate base class (grep audit).

---

## Phase 7 — Tasks F & G (Linux Workstation Readiness)

### 7.1 — Linux Validation Harness (Task F)

| Field | Value |
|-------|-------|
| **Priority** | P0 |
| **Complexity** | M |
| **Dependencies** | 2.3, 1.4 |

**Requirements**
- Add `tools/linux_smoke_test.py` (or `scripts/`): checks permissions, imports, Backend instantiation, calls representative slots.
- Add `docs/LINUX_TESTING.md` checklist.

**Acceptance Criteria**
- Script runs with `python tools/linux_smoke_test.py` exit 0 on dev machine (no hardware required).
- Documents hardware validation steps separately.

---

### 7.2 — Architecture User Guide (Task G)

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Complexity** | M |
| **Dependencies** | 5.5, 7.1 |

**Requirements**
- `docs/ARCHITECTURE_GUIDE.md`: how to add a FeatureHandler, Backend slot, QML surface, test patterns.
- Cross-link EXPANSION_EXECUTION_PLAN and LOGITECH_DEVICE_COMPANION_DESIGN.

**Acceptance Criteria**
- Guide includes copy-paste template for `UltraThinHandler` + Backend + test.
- Reviewed for accuracy against `ReportRateHandler` as reference implementation.

---

### 7.3 — Update PROJECT_PLAN.md to Reflect Completion

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Complexity** | S |
| **Dependencies** | All phases |

**Requirements**
- Rewrite "Current State" and "In Progress" to match delivered work.
- Remove stale gaps (keyboard UI, test harness) if completed.

**Acceptance Criteria**
- Third-party reader can understand project state in <5 min.
- Matches test suite status and feature list.

---

## Dependency Graph (Critical Path)

```
0.1 → 0.2 → 1.1 → 1.2 → 1.4 → 2.1 → 2.2 → 2.3
                                      ↓
                              4.1 → 4.6 → 6.1
                                      ↓
                              7.1 → 7.2 → 7.3 (closure)
```

---

## Self-Review Checklist (Plan Quality Gate)

| Check | Covered? |
|-------|----------|
| All Section D partial items mapped to tasks | ✅ 4.1–4.8 |
| All Section E Backend gaps mapped | ✅ 2.1–2.3 |
| All explicit code TODOs | ✅ 1.3 |
| All hid_gesture placeholders | ✅ 4.2, 4.7 |
| Upstream sync first | ✅ 0.1–0.2 |
| P0 test regressions | ✅ 1.1–1.4 |
| High-risk items scheduled with deps | ✅ 4.6, 5.2, 6.1 |
| Strategic advice (harness before surgery) | ✅ Phase 7 before 5.2 |
| Measurable ACs per task | ✅ |
| Complexity estimates | ✅ S/M/L/XL |
| Progress dashboard | ✅ |
| TASK-003 polish | ✅ 3.3 |
| Stale docs / duplicates | ✅ 0.3 |
| logi_device duplication | ✅ 0.4 |
| G502 from upstream | ✅ 0.1, 0.2, 4.8 |

**Plan review result:** APPROVED — no blocking gaps identified.

---

## Execution Log

| Task | Started | Completed | Commit |
|------|---------|-----------|--------|
| 0.1 | 2026-06-19 | | |

---

*Living document — update Progress Dashboard and Execution Log after each task.*