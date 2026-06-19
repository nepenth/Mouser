# Linux Workstation Testing Guide

Quick validation paths for Mouser on Linux (especially CachyOS / KDE Plasma / Wayland).

## Automated Smoke Test (No Hardware)

From the repository root with the virtualenv activated:

```bash
source .venv/bin/activate
python tools/linux_smoke_test.py
```

This verifies imports, Linux permission reporting, offscreen Qt startup, Backend instantiation, and representative architecture-handler slots with safe no-engine defaults.

## Full Unit Suite

```bash
python -m unittest discover -s tests
```

CI-equivalent:

```bash
python -m py_compile main_qml.py core/*.py ui/*.py
python -m unittest discover -s tests
```

## One-Time Device Permissions

```bash
./packaging/linux/install-linux-permissions.sh
```

Reconnect Logitech devices after running. Requires access to `/dev/hidraw*`, `/dev/input/event*`, and `/dev/uinput`.

## Python REPL — Architecture Handlers

```bash
source .venv/bin/activate
python -c "
import os; os.environ['QT_QPA_PLATFORM']='offscreen'
from PySide6.QtWidgets import QApplication
from unittest.mock import patch
from core.config import DEFAULT_CONFIG
from ui.backend import Backend
app = QApplication([])
with patch('ui.backend.load_config', return_value=DEFAULT_CONFIG.copy()):
    b = Backend(engine=None)
print('readReportRate:', b.readReportRate())
print('readDeviceMode:', b.readDeviceMode())
print('getDeviceType:', b.getDeviceType())
"
```

With hardware connected and Mouser running, use the same `Backend` methods after the engine is wired — they delegate to `Engine` → `FeatureHandler`.

## Hardware Validation Checklist

1. Plug G502 X Lightspeed receiver + MX Mechanical Mini Bolt receiver.
2. Launch `python main_qml.py` (or packaged binary).
3. Confirm G502 appears with **g502** layout (not generic_mouse).
4. Open **Keyboard** page — backlight + FN inversion when MX Mechanical Mini is active HID++ device.
5. Toggle per-device **Host Control Permissions** — settings persist across restart.
6. Optional: enable backlight key diversion; assign actions to `backlight_up` / `backlight_down`.
7. Litra Beam: `setLitraIllumination` / `readLitraIllumination` via Backend when connected.

## Logs

```text
$XDG_STATE_HOME/Mouser/logs/mouser.log
```

Default: `~/.local/state/Mouser/logs/mouser.log`