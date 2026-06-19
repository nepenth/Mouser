# Building & Testing Mouser on CachyOS (KDE Plasma / Wayland)

This guide is for **CachyOS** with **KDE Plasma on Wayland**. Generic Linux notes also live in [README.md](README.md#build-from-source) and [DEVELOPMENT.md](DEVELOPMENT.md).

## Prerequisites

- **CachyOS** (Arch-based) with **KDE Plasma** and a **Wayland** session (`echo $XDG_SESSION_TYPE` → `wayland`)
- **Python 3.10+** (3.12–3.14 tested in CI / local dev)
- A supported **Logitech HID++** mouse and/or keyboard (USB receiver or Bluetooth)
- **Logitech Options+ must not be running** — it conflicts with HID++ access

### System packages (pacman)

```bash
sudo pacman -S --needed \
  git python python-pip \
  pyside6 qt6-declarative qt6-svg \
  hidapi python-hidapi python-evdev python-pillow \
  udev
```

Optional but recommended on **KDE Wayland** for per-app profile switching:

```bash
# kdotool is not in official repos; install from AUR (yay/paru)
yay -S kdotool
```

`xdotool` is a fallback for XWayland windows; install with `sudo pacman -S xdotool` if needed.

## 1. Clone and set up the Python environment

```bash
git clone https://github.com/TomBadash/Mouser.git
cd Mouser
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On CachyOS you can also use system packages for some deps (`python-hidapi`, `python-evdev`, `pyside6`) and only `pip install pyinstaller` when packaging — the venv + `requirements.txt` path is the most reproducible for development.

## 2. Run automated tests (no hardware)

```bash
source .venv/bin/activate

# Quick smoke test (imports, Qt offscreen, Backend slots)
python tools/linux_smoke_test.py

# Full unit suite (~700 tests)
python -m unittest discover -s tests
```

CI-equivalent compile + test:

```bash
python -m py_compile main_qml.py core/*.py ui/*.py
python -m unittest discover -s tests
```

See also [docs/LINUX_TESTING.md](docs/LINUX_TESTING.md) for REPL checks and a hardware validation checklist.

## 3. One-time device permissions

Mouser needs `/dev/hidraw*`, `/dev/input/event*`, and `/dev/uinput`. Run once (uses `pkexec` / `sudo`):

```bash
./packaging/linux/install-linux-permissions.sh
```

Then **reconnect** Logitech devices, **fully quit** Mouser, and launch again. On CachyOS with systemd-logind, `uaccess` in the udev rule usually suffices; if access is still denied after relogin, add your user to the `input` group:

```bash
sudo usermod -aG input "$USER"
# log out and back in
```

## 4. Run from source (dev build)

In a **Plasma Wayland** session:

```bash
source .venv/bin/activate
python main_qml.py
```

Tray-first launch:

```bash
python main_qml.py --start-hidden
```

Logs: `~/.local/state/Mouser/logs/mouser.log`  
Config: `~/.config/Mouser/config.json`

### KDE / Wayland notes

- Per-app profiles use **`kdotool`** on KDE Wayland; without it, Mouser falls back to the default profile.
- Quit **Logitech Options+** before testing HID++ features.
- If the app menu entry looks stale after moving the checkout, launch once from the new path so Mouser can refresh `~/.local/share/applications/io.github.tombadash.mouser.desktop`.

## 5. Build a portable PyInstaller bundle

```bash
source .venv/bin/activate
pip install pyinstaller
pyinstaller Mouser-linux.spec --noconfirm
```

Output: `dist/Mouser/` — run `./dist/Mouser/Mouser` from that directory (or zip the folder for distribution).

## 6. Install as a native package (paru — recommended)

Mouser ships **paru/makepkg** definitions under `packaging/aur/`. This installs `/usr/bin/mouser` using the system Python + Qt stack (best fit for CachyOS / KDE Plasma Wayland).

### Build-time install from your checkout

```bash
cd /path/to/Mouser
paru -P ./packaging/aur/mouser-local
```

Equivalent without paru:

```bash
cd packaging/aur/mouser-local
makepkg -si
```

`mouser-local` packages the **current working tree** (including uncommitted changes). Version looks like `3.6.0.r<git-rev>.<hash>.local`.

### Other package flavors

| Command | When to use |
|---------|-------------|
| `paru -P ./packaging/aur/mouser-local` | Local dev (this checkout) |
| `paru -P ./packaging/aur/mouser-git` | Remote `master` from GitHub |
| `paru -P ./packaging/aur/mouser` | Tagged release (`v$pkgver` must exist) |

Full maintainer docs: [packaging/aur/README.md](packaging/aur/README.md)

### After install

```bash
sudo /usr/share/mouser/install-linux-permissions.sh   # if HID access fails
reconnect Logitech receivers
mouser
# or tray-first:
mouser --start-hidden
```

Release `pkgver` is synced from `core/version.py` via `./packaging/aur/sync-pkgver.sh`.

## 7. Hardware smoke checklist (CachyOS workstation)

1. Plug receivers (e.g. G502 X + MX Mechanical Mini).
2. Launch `python main_qml.py`.
3. Confirm the mouse page shows the expected device layout (not `generic_mouse` for known devices).
4. Open **Keyboard** — host backlight / FN inversion when MX Mechanical Mini is the active HID++ device.
5. Toggle **Host Control Permissions** and optional key diversion; restart Mouser and confirm persistence.
6. Switch foreground apps on Plasma Wayland — per-app profiles should update when `kdotool` is installed.

## Troubleshooting

| Symptom | Check |
|--------|--------|
| No HID++ / device not found | Options+ quit? Permissions script run? Receiver reconnected? |
| Permission banner in UI | `./packaging/linux/install-linux-permissions.sh`, relogin |
| Profiles never switch on Wayland | `which kdotool` — install from AUR |
| Qt / QML import errors from source | `pyside6` and `qt6-declarative` installed; use project venv |
| Import errors for `evdev` / `hid` | `python-evdev` and `python-hidapi` via pacman or venv pip |

Thread dump while running: `kill -USR1 $(pgrep -f main_qml.py)`