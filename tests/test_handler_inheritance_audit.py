"""Static audit: every core/devices/*_handler.py class inherits FeatureHandler hierarchy."""

from __future__ import annotations

import importlib
import inspect
import unittest
from pathlib import Path

from core.logi_device import (
    DefaultThinHandler,
    FeatureHandler,
    RecommendedThinHandler,
    SimpleDelegationHandler,
    ThinDelegationHandler,
    UltraThinHandler,
)

HANDLERS_DIR = Path(__file__).resolve().parents[1] / "core" / "devices"

# Documented convenience bases (all are FeatureHandler subclasses).
APPROVED_HANDLER_BASES = frozenset(
    {
        FeatureHandler,
        SimpleDelegationHandler,
        ThinDelegationHandler,
        DefaultThinHandler,
        RecommendedThinHandler,
        UltraThinHandler,
    }
)


def _discover_handler_modules() -> list[Path]:
    return sorted(HANDLERS_DIR.glob("*_handler.py"))


def _handler_class_for_module(module_name: str):
    module = importlib.import_module(module_name)
    candidates = [
        obj
        for name, obj in inspect.getmembers(module, inspect.isclass)
        if name.endswith("Handler") and obj.__module__ == module_name
    ]
    if len(candidates) != 1:
        raise AssertionError(
            f"{module_name}: expected exactly one *Handler class, found "
            f"{[c.__name__ for c in candidates]}"
        )
    return candidates[0]


class HandlerInheritanceAuditTests(unittest.TestCase):
    def test_handler_module_count_meets_minimum(self):
        modules = _discover_handler_modules()
        self.assertGreaterEqual(
            len(modules),
            19,
            f"expected >=19 handler modules, found {len(modules)}",
        )

    def test_each_handler_inherits_approved_base(self):
        failures: list[str] = []
        audited: list[tuple[str, str, str]] = []

        for path in _discover_handler_modules():
            module_name = f"core.devices.{path.stem}"
            handler_cls = _handler_class_for_module(module_name)
            direct_base = handler_cls.__bases__[0]

            audited.append((path.name, handler_cls.__name__, direct_base.__name__))

            if not issubclass(handler_cls, FeatureHandler):
                failures.append(
                    f"{handler_cls.__name__} ({module_name}) is not a FeatureHandler subclass"
                )
            elif direct_base not in APPROVED_HANDLER_BASES:
                failures.append(
                    f"{handler_cls.__name__} ({module_name}) inherits "
                    f"{direct_base.__name__}; expected one of "
                    f"{sorted(b.__name__ for b in APPROVED_HANDLER_BASES)}"
                )

        self.assertEqual(failures, [])
        self.assertGreaterEqual(len(audited), 19, audited)


if __name__ == "__main__":
    unittest.main()