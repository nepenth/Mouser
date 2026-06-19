"""Tests for LogitechDevice subclasses and create_logitech_device factory (Task 5.1)."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from core.hid_features import FEAT_ADJ_DPI, FEAT_BACKLIGHT2
from core.logi_device import (
    KeyboardDevice,
    LogitechDevice,
    MouseDevice,
    OtherDevice,
    create_logitech_device,
    maybe_attach_handler,
)
from core.logi_devices import build_connected_device_info


class _FeatureListener(SimpleNamespace):
    """Minimal listener stub with optional feature discovery hooks."""

    def _discovered_feature_ids(self):
        return tuple(getattr(self, "_feature_ids", ()))


class _StubHandler:
    def __init__(self, device, listener):
        self.device = device
        self.listener = listener


class LogitechDeviceFactoryTests(unittest.TestCase):
    def test_explicit_kind_returns_mouse_subclass(self):
        dev = create_logitech_device("mouse", listener=None, cfg={}, product_id=0x409F, name="G502 X")

        self.assertIsInstance(dev, MouseDevice)
        self.assertEqual(dev.kind, "mouse")
        self.assertEqual(dev.product_id, 0x409F)

    def test_explicit_kind_returns_keyboard_subclass(self):
        dev = create_logitech_device(
            "keyboard",
            listener=None,
            cfg={},
            product_id=0xB367,
            name="MX Mechanical Mini",
        )

        self.assertIsInstance(dev, KeyboardDevice)
        self.assertEqual(dev.kind, "keyboard")

    def test_explicit_kind_returns_other_subclass_for_litra(self):
        dev = create_logitech_device(
            "other",
            listener=None,
            cfg={},
            product_id=0x0897,
            name="Litra Beam",
        )

        self.assertIsInstance(dev, OtherDevice)
        self.assertEqual(dev.kind, "other")

    def test_factory_classifies_mouse_from_dpi_features(self):
        listener = _FeatureListener(_feature_ids=(FEAT_ADJ_DPI,))
        dev = create_logitech_device(
            None,
            listener=listener,
            cfg={},
            product_id=0x409F,
            name="G502 X",
        )

        self.assertIsInstance(dev, MouseDevice)
        self.assertEqual(dev.kind, "mouse")

    def test_factory_classifies_keyboard_from_backlight_features(self):
        listener = _FeatureListener(_feature_ids=(FEAT_BACKLIGHT2,))
        dev = create_logitech_device(
            None,
            listener=listener,
            cfg={},
            product_id=0xB367,
            name="MX Mechanical Mini",
        )

        self.assertIsInstance(dev, KeyboardDevice)
        self.assertEqual(dev.kind, "keyboard")

    def test_factory_classifies_litra_as_other_from_name(self):
        listener = _FeatureListener(_feature_ids=())
        dev = create_logitech_device(
            None,
            listener=listener,
            cfg={},
            product_id=0x0897,
            name="Litra Beam",
        )

        self.assertIsInstance(dev, OtherDevice)
        self.assertEqual(dev.kind, "other")

    def test_factory_uses_cached_device_kind_from_connected_inventory(self):
        connected = build_connected_device_info(
            product_id=0xB367,
            product_name="MX Mechanical Mini",
            device_identity={"device_kind": "keyboard"},
        )
        listener = _FeatureListener(connected_device=connected, _feature_ids=(FEAT_ADJ_DPI,))
        dev = create_logitech_device(None, listener=listener, cfg={}, product_id=0xB367, name="MX Mechanical Mini")

        self.assertIsInstance(dev, KeyboardDevice)
        self.assertEqual(dev.kind, "keyboard")

    def test_unknown_kind_falls_back_to_base_logitech_device(self):
        dev = create_logitech_device(
            None,
            listener=_FeatureListener(_feature_ids=()),
            cfg={},
            product_id=0x0001,
            name="Mystery Device",
        )

        self.assertIsInstance(dev, LogitechDevice)
        self.assertNotIsInstance(dev, (MouseDevice, KeyboardDevice, OtherDevice))
        self.assertEqual(dev.kind, "unknown")

    def test_factory_stores_listener_and_cfg(self):
        listener = _FeatureListener(_feature_ids=())
        cfg = {"foo": "bar"}
        dev = create_logitech_device("mouse", listener=listener, cfg=cfg, product_id=1, name="Mouse")

        self.assertIs(dev._listener, listener)
        self.assertEqual(dev._cfg, cfg)


class MaybeAttachHandlerSubclassTests(unittest.TestCase):
    def test_maybe_attach_handler_creates_mouse_device_for_dpi_listener(self):
        listener = _FeatureListener(
            _dpi_idx=0x10,
            _feature_ids=(FEAT_ADJ_DPI,),
            connected_device=SimpleNamespace(product_id=0x409F, name="G502 X", key="g502"),
        )
        dev = maybe_attach_handler(
            listener=listener,
            handler_cls=_StubHandler,
            cfg={},
            feature_attr="_dpi_idx",
            handler_name="dpi",
        )

        self.assertIsNotNone(dev)
        self.assertIsInstance(dev, MouseDevice)
        self.assertTrue(dev.has_handler("dpi"))

    def test_maybe_attach_handler_creates_other_device_for_litra_listener(self):
        listener = _FeatureListener(
            _litra_illumination_idx=0x12,
            _feature_ids=(),
            connected_device=SimpleNamespace(product_id=0x0897, name="Litra Beam", key="litra"),
        )
        dev = maybe_attach_handler(
            listener=listener,
            handler_cls=_StubHandler,
            cfg={},
            device_name_fallback="Litra Beam",
            product_id_fallback=0x0897,
            feature_attr="_litra_illumination_idx",
            handler_name="litra_illumination",
        )

        self.assertIsNotNone(dev)
        self.assertIsInstance(dev, OtherDevice)
        self.assertTrue(dev.has_handler("litra_illumination"))

    def test_maybe_attach_handler_creates_keyboard_device_for_backlight_listener(self):
        listener = _FeatureListener(
            _backlight2_idx=0x14,
            _feature_ids=(FEAT_BACKLIGHT2,),
            connected_device=SimpleNamespace(
                product_id=0xB367,
                name="MX Mechanical Mini",
                key="mx_mechanical_mini",
            ),
        )
        dev = maybe_attach_handler(
            listener=listener,
            handler_cls=_StubHandler,
            cfg={},
            feature_attr="_backlight2_idx",
            handler_name="backlight",
        )

        self.assertIsNotNone(dev)
        self.assertIsInstance(dev, KeyboardDevice)
        self.assertTrue(dev.has_handler("backlight"))


if __name__ == "__main__":
    unittest.main()