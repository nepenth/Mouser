"""Unit tests for core.keyboard_diversion (EXPANSION 6.3)."""

import copy
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from core.config import DEFAULT_CONFIG
from core.keyboard_diversion import (
    DIVERT_EVENT_ALIASES,
    MX_MECHANICAL_MINI_DIVERT_SPECS,
    build_keyboard_extra_diverts,
    is_mx_mechanical_mini_device,
    resolve_divert_cid,
    resolve_diverted_keyboard_action,
)


class KeyboardDiversionCatalogTests(unittest.TestCase):
    def test_is_mx_mechanical_mini_by_pid_and_name(self):
        self.assertTrue(is_mx_mechanical_mini_device(product_id=0xB367))
        self.assertTrue(is_mx_mechanical_mini_device(name="MX Mechanical Mini"))
        self.assertFalse(is_mx_mechanical_mini_device(product_id=0xB023, name="MX Master 3S"))

    def test_resolve_divert_cid_prefers_task_mapping(self):
        spec = next(s for s in MX_MECHANICAL_MINI_DIVERT_SPECS if s.event_stem == "keyboard_volume_up")
        cid = resolve_divert_cid(
            spec,
            reprog_cids=frozenset({0x00C9, 0x00E9}),
            task_to_cid={0x00E9: 0x00E9, 0x0001: 0x00C9},
        )
        self.assertEqual(cid, 0x00E9)

    def test_resolve_divert_cid_falls_back_to_candidates(self):
        spec = next(s for s in MX_MECHANICAL_MINI_DIVERT_SPECS if s.event_stem == "keyboard_mute")
        cid = resolve_divert_cid(spec, reprog_cids=frozenset({0x00C7}))
        self.assertEqual(cid, 0x00C7)

    def test_resolve_diverted_keyboard_action_uses_button_and_alias_keys(self):
        mappings = {
            "keyboard_volume_up": "browser_back",
            "mute": "browser_forward",
        }
        self.assertEqual(
            resolve_diverted_keyboard_action(mappings, "keyboard_volume_up_down"),
            "browser_back",
        )
        self.assertEqual(
            resolve_diverted_keyboard_action(mappings, "keyboard_mute_down"),
            "browser_forward",
        )
        self.assertEqual(resolve_diverted_keyboard_action(mappings, "keyboard_search_down"), "none")

    def test_divert_event_aliases_cover_media_keys(self):
        self.assertIn("volume_up", DIVERT_EVENT_ALIASES)
        self.assertIn("search", DIVERT_EVENT_ALIASES)


class KeyboardMediaDiversionGatingTests(unittest.TestCase):
    VOLUME_UP_CID = 0x00C9
    VOLUME_DOWN_CID = 0x00C8
    MUTE_CID = 0x00C7
    SEARCH_CID = 0x00D4

    def _mx_mini_device(self, key="B367"):
        return SimpleNamespace(key=key, name="MX Mechanical Mini", product_id=0xB367)

    def _cfg(self, device_key, kmp):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg.setdefault("devices", {})[device_key] = {"keyboard_middle_path": kmp}
        return cfg

    def test_build_extra_diverts_registers_media_cids_when_opt_in_true(self):
        cfg = self._cfg(
            "B367",
            {
                "allow_diversion_volume": True,
                "allow_diversion_mute": True,
                "allow_diversion_search": True,
            },
        )
        dev = self._mx_mini_device()
        factory = Mock(side_effect=lambda stem: {"on_down": Mock(), "on_up": Mock()})

        extra = build_keyboard_extra_diverts(
            cfg=cfg,
            device=dev,
            dispatch_factory=factory,
            reprog_cids=frozenset(
                {self.VOLUME_UP_CID, self.VOLUME_DOWN_CID, self.MUTE_CID, self.SEARCH_CID}
            ),
        )

        self.assertIn(self.VOLUME_UP_CID, extra)
        self.assertIn(self.VOLUME_DOWN_CID, extra)
        self.assertIn(self.MUTE_CID, extra)
        self.assertIn(self.SEARCH_CID, extra)
        self.assertEqual(factory.call_count, 4)

    def test_build_extra_diverts_skips_media_cids_when_opt_in_false(self):
        cfg = self._cfg("B367", {})
        dev = self._mx_mini_device()

        extra = build_keyboard_extra_diverts(
            cfg=cfg,
            device=dev,
            dispatch_factory=lambda stem: {"on_down": Mock(), "on_up": Mock()},
            reprog_cids=frozenset(
                {self.VOLUME_UP_CID, self.VOLUME_DOWN_CID, self.MUTE_CID, self.SEARCH_CID}
            ),
        )

        self.assertEqual(extra, {})

    def test_build_extra_diverts_only_registers_enabled_flags(self):
        cfg = self._cfg("B367", {"allow_diversion_mute": True})
        dev = self._mx_mini_device()

        extra = build_keyboard_extra_diverts(
            cfg=cfg,
            device=dev,
            dispatch_factory=lambda stem: {"on_down": Mock(), "on_up": Mock()},
            reprog_cids=frozenset({self.MUTE_CID, self.VOLUME_UP_CID}),
        )

        self.assertEqual(set(extra.keys()), {self.MUTE_CID})


if __name__ == "__main__":
    unittest.main()