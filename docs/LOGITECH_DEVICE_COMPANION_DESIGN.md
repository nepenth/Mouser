# Mouser → Logitech Device Companion Design (Option B)

**Date:** 2026-05-18  
**Author:** Grok (with user input)  
**Status:** Draft for review and parallel execution

## 1. Vision & Guiding Principles

**Vision**  
Mouser evolves from a specialized Logitech mouse remapper into a **local, privacy-first Logitech HID++ device companion** that gives users excellent onboard + light, consistent host-side enhancements across macOS and Linux (especially KDE Plasma / Wayland) — without ever needing Logitech Options or G HUB.

**Target User (Primary)**  
- KVM user with multiple Logitech devices (G502 X Lightspeed + MX Mechanical Mini keyboard on separate receivers, plus interest in Litra Beam and webcam).
- Strongly prefers **onboard profiles as source of truth** for cross-machine consistency.
- Wants useful host conveniences (DPI, ratchet, backlight, battery visibility, selective diversion) that are **safe, non-destructive, and optional**.

**Guiding Principles**
1. **Onboard is Sacred** — Host-side changes must be clearly temporary or opt-in. The mouse/keyboard must remain fully functional with zero software running.
2. **Device-Centric, Not Mouse-Centric** — Keyboards, mice, and eventually lights/webcams are first-class peers.
3. **Graceful Degradation** — If we cannot grab input (common on gaming mice or when other tools are present), the app still provides value (battery, backlight, DPI, status).
4. **Multi-Receiver Reality** — Users routinely have a Lightspeed receiver + a Bolt receiver. The app must handle this cleanly and efficiently.
5. **Middle Path for Keyboards** — Start with high-value, low-risk features (battery, backlight, FN inversion, selective key diversion) rather than attempting full keyboard remapping parity with the mouse side.
6. **Extensibility over Big Bang** — Use a feature-handler + device-type pattern so adding new devices or capabilities is incremental.
7. **Testability & Validation** — Every major change must have clear acceptance criteria and automated + manual validation paths.

## 2. Current State Assessment (May 2026)

- Strong HID++ foundation (feature discovery, REPROG_V4 walking, receiver devIdx probing, battery, DPI, wheel features).
- Excellent for MX Master / Anywhere mice.
- G502 X Lightspeed support in progress (decoupled feature discovery, ratchet via 0x2121, onboard awareness).
- Keyboard probing already happens (MX Mechanical Mini on Bolt receiver shows rich REPROG + BACKLIGHT2 + FN inversion).
- Major gaps:
  - Single-device / single-receiver assumptions in many places.
  - Mouse-only assumptions (gesture diversion, RawXY, evdev mouse grab) bleed into keyboard paths.
  - No first-class multi-device UI or model.
  - No backlight or keyboard-specific handlers yet.

## 3. Target Device Model

```text
LogitechReceiver (c547 Lightspeed, c548 Bolt, etc.)
├── LogitechDevice
│   ├── MouseDevice (G502 X, MX Master, etc.)
│   │   └── Capabilities: DPI, SmartShift / Ratchet, ReprogDiversion, Battery, Wheel
│   ├── KeyboardDevice (MX Mechanical Mini, MX Keys, etc.)
│   │   └── Capabilities: Backlight, FN Inversion, ReprogDiversion (keys), Battery, HostSwitch
│   └── OtherDevice (Litra Beam, webcam, etc.)
│       └── Capabilities: Illumination, Camera controls, ...
```

Each `LogitechDevice` owns:
- Identity (name, WPID, transport, receiver)
- Feature index cache
- Capability inventory (what it actually supports)
- Optional input handler (mouse hook vs keyboard hook vs none)
- Settings / state (onboard vs host mode, current backlight level, etc.)

## 4. Architecture Layers (Proposed)

1. **Transport / Discovery Layer** (already strong)
   - Multi-receiver enumeration
   - Direct device vs receiver slot probing
   - Early device-type classification (from name + WPID + feature set)

2. **Device Abstraction Layer** (new)
   - `LogitechDevice` base
   - `MouseDevice`, `KeyboardDevice` subclasses
   - `FeatureHandler` registry (BatteryHandler, BacklightHandler, ReprogHandler, DPIHandler, RatchetHandler, FNInversionHandler, ...)

3. **Input Handling Layer** (specialized)
   - Mouse: existing evdev / CGEventTap / WH_MOUSE_LL + uinput
   - Keyboard: new, lighter path (only divert selected keys when user opts in)
   - Fallback: "controls only" mode when grab is impossible or undesirable

4. **UI / Backend Layer**
   - Sidebar or tab showing all connected Logitech devices
   - Per-device pages (MousePage already exists; new KeyboardPage and DeviceOverview)
   - Capability-driven UI (only show backlight slider if `BACKLIGHT2` is present)

5. **Persistence & Policy Layer**
   - Per-device "respect onboard" flag
   - Per-device "allow host diversion" whitelist
   - Last-known state replay on reconnect (already done for SmartShift/DPI)

## 5. Phased Roadmap with Acceptance Criteria

### Phase 0 – Multi-Receiver Hygiene & Device Typing (Foundation)
**Goal:** Two receivers (Bolt + Lightspeed) no longer interfere. Keyboard no longer causes mouse-side timeouts or log spam.

**Acceptance Criteria**
- Mouser launches cleanly with both receivers plugged in.
- G502 X on Lightspeed receiver reaches "Connected" state with DPI control within 10 seconds, even when Bolt + keyboard is also present.
- No mouse-style gesture diversion attempts are made against the MX Mechanical Mini (or any device whose primary kind is `keyboard`).
- Clear logging: "Treating device as KeyboardDevice (MX Mechanical Mini) — skipping mouse gesture paths."
- Graceful fallback when evdev grab fails: device still shows as connected, HID++ controls (DPI, backlight, battery) remain functional.

### Phase 1 – Basic Multi-Device Visibility
**Goal:** User can see both their mouse and keyboard in the app.

**Acceptance Criteria**
- Sidebar or device list shows "G502 X Lightspeed" and "MX Mechanical Mini" as separate entries.
- Each shows basic status: transport/receiver, battery %, connection state.
- Selecting a device shows the appropriate page (existing MousePage or new lightweight Keyboard status page).

### Phase 2 – MX Mechanical Mini "Middle Path" Features
**Goal:** Deliver immediately useful host enhancements for the keyboard without overreach.

**Target Features (Middle Path)**
- Battery reporting (already discovered via `UNIFIED_BATTERY`)
- Backlight control via `BACKLIGHT2 {1982}` (brightness on/off, possibly simple levels)
- FN inversion toggle (`K375S FN INVERSION`)
- Optional diversion of a small, safe set of keys (Backlight Up/Down, Volume Up/Down, Mute) with host actions (if user enables per-key)

**Acceptance Criteria**
- Backlight can be turned on/off and brightness adjusted from Mouser UI; change survives reconnect when "respect onboard" is off, or is clearly marked temporary.
- FN inversion toggle works and is reflected in the UI.
- User can enable "Allow host diversion for selected keys" for the keyboard; diverted keys can trigger normal Mouser actions (global shortcuts, etc.) without breaking onboard profile for other keys.
- No attempt to take over the entire keyboard or replace onboard profiles.

### Phase 3 – Architecture Generalization & Extensibility
**Goal:** Long-term maintainability.

**Acceptance Criteria**
- New device types or features can be added with minimal changes to core connection loop.
- Existing mouse experience has not regressed (all current G502 X + MX Master tests still pass).
- Clear separation between "input interception" concerns and "HID++ feature control" concerns.

### Phase 4 – Polish & Additional Devices
- Litra Beam illumination (low priority)
- Improved keyboard UI (key capture dialog for diversion)
- Per-device "KVM / Onboard Mode" preset that sets sensible defaults (no grab, only controls + battery/backlight)

## 6. Keyboard "Middle Path" Definition (Explicit Scope)

**In Scope (Phase 2)**
- Read battery
- Control backlight (on/off + level via BACKLIGHT2)
- Toggle FN inversion
- Per-key opt-in diversion for a handful of high-value keys (Backlight, media, search, etc.)
- Clear UI labeling: "These changes are host-side only and may be lost when the keyboard reconnects or changes host"

**Out of Scope (at least until Phase 3+)**
- Full onboard profile editing for the keyboard (use Solaar or G HUB for that)
- Complex macros or layers managed from Mouser
- Replacing the keyboard's onboard behavior entirely

This "middle path" matches the user's stated preference: "in the middle for the keyboard in terms of aggressive and simple/easy/safe".

## 7. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Mouse experience regresses due to generalization | Strong test harness + sub-agent validation agents that run full mouse test suite on every change |
| Keyboard diversion is confusing or fights onboard | Very explicit UI + per-key opt-in + "respect onboard" default = true |
| Multiple receivers cause connection instability | Phase 0 focus + extensive logging + timeout/backoff improvements |
| UI becomes cluttered | Device list + per-device pages; hide advanced controls behind "Advanced" or capability flags |
| Scope creep into full keyboard remapper | Strict Phase 2 acceptance criteria + design review sub-agents |

## 8. Next Execution Steps (Transition to Option A)

After this design is reviewed and accepted:

1. Create detailed task breakdown per phase with acceptance criteria.
2. Spawn parallel sub-agents:
   - Architecture & Interface Design Agent
   - Multi-Receiver + Device Typing Implementation Agent
   - MX Mechanical Mini Backlight + Battery Agent
   - Test & Validation Agent (acceptance criteria checker)
   - Code Review / Safety Agent
3. Continuous validation loop: implementation agents push changes → validation agents run tests and acceptance checks → feedback loop until criteria are green.

---

This document will be the single source of truth for acceptance criteria and design decisions as we execute with high concurrency.