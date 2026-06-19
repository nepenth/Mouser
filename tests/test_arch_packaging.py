"""Validate Arch / AUR packaging metadata and install helpers."""

import os
import re
import stat
import subprocess
import unittest

from core.version import APP_VERSION


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUR = os.path.join(ROOT, "packaging", "aur")


class ArchPackagingTests(unittest.TestCase):
    def test_package_mouser_helper_exists(self):
        helper = os.path.join(AUR, "package-mouser.sh")
        self.assertTrue(os.path.isfile(helper))

    def test_mouser_install_exists(self):
        install = os.path.join(AUR, "mouser.install")
        self.assertTrue(os.path.isfile(install))

    def test_local_pkgbuild_declares_core_dependencies(self):
        pkgbuild = os.path.join(AUR, "mouser-local", "PKGBUILD")
        with open(pkgbuild, encoding="utf-8") as handle:
            text = handle.read()
        for dep in ("pyside6", "python-hidapi", "python-evdev", "qt6-declarative"):
            with self.subTest(dep=dep):
                self.assertIn(f"'{dep}'", text)

    def test_release_pkgver_matches_app_version(self):
        pkgbuild = os.path.join(AUR, "mouser", "PKGBUILD")
        with open(pkgbuild, encoding="utf-8") as handle:
            text = handle.read()
        match = re.search(r"^pkgver=(.+)$", text, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1).strip(), APP_VERSION)

    def test_sync_pkgver_script_updates_release_pkgbuild(self):
        script = os.path.join(AUR, "sync-pkgver.sh")
        self.assertTrue(os.stat(script).st_mode & stat.S_IXUSR)
        subprocess.run(["/bin/bash", script], cwd=ROOT, check=True)
        with open(os.path.join(AUR, "mouser", "PKGBUILD"), encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn(f"pkgver={APP_VERSION}", text)

    def test_desktop_and_icon_assets_exist(self):
        desktop = os.path.join(
            ROOT, "packaging", "linux", "io.github.tombadash.mouser.desktop.in"
        )
        icon = os.path.join(
            ROOT,
            "packaging",
            "linux",
            "icons",
            "hicolor",
            "128x128",
            "apps",
            "io.github.tombadash.mouser.png",
        )
        self.assertTrue(os.path.isfile(desktop))
        self.assertTrue(os.path.isfile(icon))

    def test_package_mouser_installs_udev_rules_in_share_and_udev(self):
        helper = os.path.join(AUR, "package-mouser.sh")
        with open(helper, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("/usr/lib/udev/rules.d/69-mouser-logitech.rules", text)
        self.assertIn("/usr/share/mouser/69-mouser-logitech.rules", text)
        self.assertIn("packaging/linux/io.github.tombadash.mouser.desktop.in", text)
        self.assertIn("packaging/linux/icons", text)

    def test_keyboard_nav_icon_exists(self):
        icon = os.path.join(ROOT, "images", "icons", "keyboard-simple.svg")
        self.assertTrue(os.path.isfile(icon))

    def test_install_permissions_script_handles_packaged_rules(self):
        script = os.path.join(ROOT, "packaging", "linux", "install-linux-permissions.sh")
        with open(script, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("/usr/lib/udev/rules.d/", text)
        self.assertIn("/usr/share/mouser/", text)

    def test_all_aur_variants_reference_shared_install(self):
        for variant in ("mouser", "mouser-git", "mouser-local"):
            pkgbuild = os.path.join(AUR, variant, "PKGBUILD")
            with open(pkgbuild, encoding="utf-8") as handle:
                text = handle.read()
            self.assertIn("package-mouser.sh", text)
            self.assertIn("mouser.install", text)


if __name__ == "__main__":
    unittest.main()