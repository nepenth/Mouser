# Architecture Guide — Adding a FeatureHandler

This guide explains how to add a new Logitech HID++ capability using the **FeatureHandler → Engine → Backend → test** pattern established in TASK-009.

**Related docs:**
- [EXPANSION_EXECUTION_PLAN.md](EXPANSION_EXECUTION_PLAN.md) — phased task list and acceptance criteria
- [LOGITECH_DEVICE_COMPANION_DESIGN.md](LOGITECH_DEVICE_COMPANION_DESIGN.md) — multi-device companion vision
- [DEFERRED.md](DEFERRED.md) — explicitly out-of-scope items (e.g. webcam)

---

## Layer overview

```
HidGestureListener (core/hid_gesture.py)
    ↑ listener methods: read_*, set_*, get_*
FeatureHandler     (core/devices/*_handler.py)
    ↑ handle_read / handle_write
Engine             (core/engine.py)
    ↑ read_* / set_* public API + lazy attachment
Backend            (ui/backend.py)
    ↑ @Slot QML/Python-callable methods
Tests              (tests/test_backend.py, tests/test_engine.py, …)
```

Each layer stays thin: the listener owns HID++ I/O; handlers delegate unless custom normalization is required; Engine adds lazy attachment and fallback; Backend exposes safe defaults when no engine is present.

---

## Reference implementation: `ReportRateHandler`

Use **`core/devices/report_rate_handler.py`** as the canonical example for a read/write thin handler.

| Piece | Location |
|-------|----------|
| Handler | `core/devices/report_rate_handler.py` |
| Listener methods | `HidGestureListener.read_report_rate` / `set_report_rate` in `core/hid_gesture.py` |
| Engine wrappers | `Engine.read_report_rate` / `set_report_rate` in `core/engine.py` |
| Lazy attachment | `Engine._maybe_attach_report_rate_handler` |
| Backend slots | `Backend.readReportRate` / `setReportRate` in `ui/backend.py` |
| Backend tests | `NewArchitectureHandlersBackendTestsA2` in `tests/test_backend.py` |

`ReportRateHandler` inherits **`DefaultThinHandler`**, which provides `is_supported()`, `handle_read()`, and `handle_write()` via listener method names.

For the **simplest read-only** case, use **`UltraThinHandler`** (see `core/devices/device_type_handler.py`).

---

## Step-by-step: add a new capability

### 1. Listener (HID++ I/O)

Add `read_my_feature` / `set_my_feature` on `HidGestureListener` in `core/hid_gesture.py`:

- Discover the feature index during `_discover_features` (store as `self._my_feature_idx`).
- Implement read/write using `self._request(self._my_feature_idx, func, payload)`.
- Return `None` / `False` when the feature is unavailable.

### 2. FeatureHandler

Create `core/devices/my_feature_handler.py`:

```python
from core.logi_device import UltraThinHandler  # or DefaultThinHandler for read+write

class MyFeatureHandler(UltraThinHandler):
    _friendly_name = "My Feature"  # optional, for logging

    def __init__(self, device, listener):
        super().__init__(
            device,
            listener,
            feature_index_attr="_my_feature_idx",
            read_method="read_my_feature",
            write_method="set_my_feature",  # omit for read-only; call _mark_as_read_only()
        )
        self._listener = listener
```

**Base class choice:**

| Base | When to use |
|------|-------------|
| `UltraThinHandler` | Pure delegation, read-only or read+write |
| `DefaultThinHandler` | Same as above; slightly older naming convention |
| `FeatureHandler` | Custom `handle_read` / `handle_write` (normalization, extra guards) |

### 3. Engine wrapper + lazy attachment

In `core/engine.py`:

**Import** (guarded, matching existing handlers):

```python
try:
    from core.devices.my_feature_handler import MyFeatureHandler
except ImportError:
    MyFeatureHandler = None
```

**Public API** (delegate + fallback):

```python
def read_my_feature(self):
    def _fallback():
        hg = self.hook._hid_gesture
        if hg and hasattr(hg, "read_my_feature"):
            return hg.read_my_feature()
        return None

    self._maybe_attach_my_feature_handler()
    return self._delegate_or_fallback(
        "_my_feature_device", "my_feature", "handle_read", _fallback
    )
```

**Lazy attachment** (copy `ReportRateHandler` pattern):

```python
def _maybe_attach_my_feature_handler(self):
    if not (MyFeatureHandler and hasattr(self, "hook")):
        return
    hg = getattr(self.hook, "_hid_gesture", None)
    if not hg or getattr(hg, "_my_feature_idx", None) is None:
        return
    if not hasattr(self, "_my_feature_device") or self._my_feature_device is None:
        dev = maybe_attach_handler(
            listener=hg,
            handler_cls=MyFeatureHandler,
            cfg=self.cfg,
            device_key_fallback=str(getattr(getattr(hg, "connected_device", None), "product_id", 0)),
            device_name_fallback="Device",
            product_id_fallback=getattr(getattr(hg, "connected_device", None), "product_id", 0),
            feature_attr="_my_feature_idx",
            handler_name="my_feature",
        )
        if dev:
            self._my_feature_device = dev
```

### 4. Backend `@Slot`

In `ui/backend.py`, add thin delegates with **safe no-engine defaults**:

```python
@Slot(result="QVariant")
def readMyFeature(self):
    """Read my feature. Host-side only, temporary."""
    if self._engine and hasattr(self._engine, "read_my_feature"):
        val = self._engine.read_my_feature()
        return val if val is not None else None
    return None

@Slot(int, result=bool)
def setMyFeature(self, value):
    """Set my feature. Host-side only, temporary."""
    if self._engine and hasattr(self._engine, "set_my_feature"):
        return bool(self._engine.set_my_feature(int(value)))
    return False
```

Convention: `False` / `None` / `[]` / `{}` / `-1` for unavailable — match sibling slots in the same section.

### 5. Tests

Add a class in `tests/test_backend.py` (mirror `NewArchitectureHandlersBackendTestsA2` / `NewArchitectureHandlersBackendTestsD`):

```python
class NewArchitectureHandlersBackendTestsMyFeature(unittest.TestCase):
    def _make_backend(self, engine=None):
        _ensure_qapp()
        with patch("ui.backend.load_config", return_value=copy.deepcopy(DEFAULT_CONFIG)):
            return Backend(engine=engine)

    def test_no_engine_returns_safe_defaults(self):
        backend = self._make_backend(engine=None)
        self.assertIsNone(backend.readMyFeature())
        self.assertFalse(backend.setMyFeature(1))

    def test_delegates_to_engine(self):
        fake_engine = _FakeEngine()
        fake_engine.read_my_feature = lambda: 42
        fake_engine.set_my_feature = lambda v: v == 42
        backend = self._make_backend(engine=fake_engine)
        self.assertEqual(backend.readMyFeature(), 42)
        self.assertTrue(backend.setMyFeature(42))
```

Optionally add listener-level tests in `tests/test_hid_gesture.py` when parse logic is non-trivial.

Update `tests/test_backend_engine_parity.py` if you add new Engine/Backend name pairs.

### 6. QML surface (optional)

Expose Backend properties/methods from the appropriate page QML file once the Python path is tested on Linux (`docs/LINUX_TESTING.md`).

---

## Copy-paste checklist

- [ ] Feature index discovered in `hid_gesture.py`
- [ ] `read_*` / `set_*` listener methods implemented
- [ ] `*Handler` class in `core/devices/` (prefer `UltraThinHandler` / `DefaultThinHandler`)
- [ ] Guarded import in `engine.py`
- [ ] `read_*` / `set_*` Engine methods with `_delegate_or_fallback`
- [ ] `_maybe_attach_*_handler` using `maybe_attach_handler`
- [ ] Backend `@Slot` methods with safe defaults
- [ ] `tests/test_backend.py` — no-engine + delegation cases
- [ ] Full suite green: `python -m unittest discover -s tests`

---

## Intentional delegation (battery example)

Not every handler needs custom parse logic. **`BatteryHandler`** intentionally delegates to `listener.read_battery()`; parsing lives in `HidGestureListener._parse_battery_response` and `_apply_pending_read_battery`. Use this pattern when the listener already owns a pending-state machine or complex I/O sequencing.