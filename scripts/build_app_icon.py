"""Build the platform icon assets from the canonical master PNG.

Inputs
------
``images/logo_icon.png``
    Canonical 1024 x 1024 RGBA master of the app icon. Conforms to the
    Apple Big Sur / Tahoe icon grid: an ~824 px squircle centred on a
    1024 px canvas with ~100 px transparent gutter on every side so
    macOS can composite the standard drop shadow without clipping.

Outputs (regenerated in place)
------------------------------
``images/AppIcon.icns``
    Multi-resolution Apple Icon Image (.icns) for the macOS bundle:
    16, 32, 128, 256, 512 + their ``@2x`` Retina variants, all derived
    by Lanczos-down-sampling the master. Consumed by ``Mouser-mac.spec``
    via ``CFBundleIconFile``.

``images/logo.ico``
    Multi-resolution Windows icon (.ico) at 16, 24, 32, 48, 64, 128, 256.
    The squircle is re-fit to ~96% of the canvas so the 16 px
    representation stays legible -- Windows taskbars do not allocate
    macOS-style gutter for drop shadows. Consumed by ``Mouser.spec`` on
    the Windows build path.

Tooling
-------
* ``iconutil`` (macOS-only, built into the OS) for ``.icns`` assembly.
* ``sips`` (macOS-only, built into the OS) for the per-size resample.
* ``Pillow`` (Python, declared in ``requirements.txt``) for the
  Windows variant resize + ``.ico`` write.

Run
---
``python scripts/build_app_icon.py`` from the repository root. Exits
non-zero with an explicit error if a required tool is missing, the
master is missing or wrong-shaped, or any sub-process fails -- so CI
can wire it into a verification stage without ambiguity.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "images" / "logo_icon.png"
OUT_ICNS = ROOT / "images" / "AppIcon.icns"
OUT_ICO = ROOT / "images" / "logo.ico"

MAC_CANVAS = 1024
WIN_CANVAS = 1024
# Apple icon grid: 824 squircle on 1024 canvas (10% gutter each side).
# Microsoft Learn: no fixed gutter; 96% fill keeps the 16 px tile
# readable on the Windows 11 taskbar.
WIN_FILL_RATIO = 980 / 1024

ICNS_SIZES = (16, 32, 128, 256, 512)
ICO_SIZES = ((16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
             (128, 128), (256, 256))


def _require_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise SystemExit(
            f"build_app_icon.py: required tool not found: {name!r}.\n"
            f"Run on macOS; iconutil and sips ship with the OS."
        )
    return path


def _validate_master() -> Image.Image:
    if not MASTER.is_file():
        raise SystemExit(f"build_app_icon.py: master missing at {MASTER}")
    image = Image.open(MASTER)
    if image.mode != "RGBA":
        raise SystemExit(
            f"build_app_icon.py: master must be RGBA, got {image.mode!r}"
        )
    if image.size != (MAC_CANVAS, MAC_CANVAS):
        raise SystemExit(
            f"build_app_icon.py: master must be {MAC_CANVAS}x{MAC_CANVAS}, "
            f"got {image.size[0]}x{image.size[1]}"
        )
    return image


def build_icns(iconutil: str, sips: str) -> None:
    with tempfile.TemporaryDirectory(prefix="mouser-iconset-") as tmp:
        iconset = Path(tmp) / "Mouser.iconset"
        iconset.mkdir()
        for size in ICNS_SIZES:
            for retina in (False, True):
                pixel = size * 2 if retina else size
                suffix = "@2x" if retina else ""
                out = iconset / f"icon_{size}x{size}{suffix}.png"
                subprocess.run(
                    [sips, "-z", str(pixel), str(pixel),
                     str(MASTER), "--out", str(out)],
                    check=True, stdout=subprocess.DEVNULL,
                )
        subprocess.run(
            [iconutil, "-c", "icns", str(iconset), "-o", str(OUT_ICNS)],
            check=True,
        )


def build_ico(master: Image.Image) -> None:
    # Lift the squircle out of the master, then re-fit it to ~96% of the
    # Windows canvas. We use the alpha channel as the squircle mask: pixels
    # with alpha > 0 belong to the squircle.
    alpha = master.split()[-1]
    bbox = alpha.getbbox()
    if bbox is None:
        raise SystemExit("build_app_icon.py: master has no visible pixels")
    squircle = master.crop(bbox)
    target_side = int(round(WIN_CANVAS * WIN_FILL_RATIO))
    w, h = squircle.size
    scale = target_side / float(max(w, h))
    fitted = squircle.resize(
        (max(1, int(round(w * scale))), max(1, int(round(h * scale)))),
        Image.LANCZOS,
    )
    canvas = Image.new("RGBA", (WIN_CANVAS, WIN_CANVAS), (0, 0, 0, 0))
    fx = (WIN_CANVAS - fitted.size[0]) // 2
    fy = (WIN_CANVAS - fitted.size[1]) // 2
    canvas.paste(fitted, (fx, fy), fitted)
    canvas.save(OUT_ICO, format="ICO", sizes=list(ICO_SIZES))


def main() -> int:
    if sys.platform != "darwin":
        raise SystemExit(
            "build_app_icon.py must run on macOS (needs iconutil + sips)."
        )
    iconutil = _require_tool("iconutil")
    sips = _require_tool("sips")
    master = _validate_master()
    build_icns(iconutil, sips)
    build_ico(master)
    print(f"wrote {OUT_ICNS}")
    print(f"wrote {OUT_ICO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
