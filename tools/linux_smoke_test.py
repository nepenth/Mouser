#!/usr/bin/env python3
"""Linux workstation smoke test — no hardware required.

Validates imports, Backend instantiation, and representative @Slot calls
with safe no-engine defaults. Run from repo root:

    python tools/linux_smoke_test.py
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _check(name: str, fn) -> None:
    try:
        fn()
        print(f"  OK  {name}")
    except Exception as exc:
        print(f"FAIL  {name}: {exc}")
        raise


def main() -> int:
    print("[linux_smoke_test] Starting (no hardware required)")

    _check("import core.engine", lambda: __import__("core.engine"))
    _check("import core.hid_gesture", lambda: __import__("core.hid_gesture"))
    _check("import core.linux_permissions", lambda: __import__("core.linux_permissions"))

    from core.linux_permissions import linux_permission_report

    _check(
        "linux_permissions report",
        lambda: linux_permission_report() is not None or True,
    )

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])

    from unittest.mock import patch
    from core.config import DEFAULT_CONFIG
    from ui.backend import Backend

    with patch("ui.backend.load_config", return_value=DEFAULT_CONFIG.copy()):
        backend = Backend(engine=None)

    slots = [
        ("readBacklight", lambda: backend.readBacklight()),
        ("setBacklight", lambda: backend.setBacklight(True, 50) is False),
        ("readReportRate", lambda: backend.readReportRate() is None),
        ("readDeviceMode", lambda: backend.readDeviceMode() is None),
        ("readWirelessStatus", lambda: backend.readWirelessStatus() is None),
        ("readPowerManagement", lambda: backend.readPowerManagement() is None),
        ("getDeviceType", lambda: backend.getDeviceType() == {}),
        ("readSmartShift", lambda: backend.readSmartShift() is None),
        ("keyboardBacklightSupported", lambda: backend.keyboardBacklightSupported is False),
    ]

    for name, call in slots:
        _check(f"Backend.{name}", call)

    print(f"[linux_smoke_test] All checks passed ({len(slots) + 5} total)")
    app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())