# Mouser — Arch / CachyOS packages (paru / makepkg)

Native packages install Mouser under `/usr/lib/mouser` with a `/usr/bin/mouser` launcher that uses the **system** Python, PySide6, and Qt6 stack (recommended on **CachyOS + KDE Plasma Wayland**).

| Package | Use when |
|---------|----------|
| **mouser-local** | Building your **current checkout** (uncommitted changes OK) |
| **mouser-git** | Tracking **remote `master`** (fork or upstream) |
| **mouser** | **Tagged release** (`v$pkgver` on GitHub) |

Application version is defined in `core/version.py` (`APP_VERSION`). Release `pkgver` is synced via `sync-pkgver.sh`.

## Quick install (CachyOS + paru)

From your Mouser git checkout:

```bash
# Recommended for local development — packages the tree you have on disk
paru -P "$(pwd)/packaging/aur/mouser-local"   # mouser-local — not mouse-local
```

Install build deps first if paru asks:

```bash
sudo pacman -S --needed base-devel git python pyside6 python-hidapi python-evdev \
  python-pillow qt6-declarative qt6-svg
```

Optional for KDE Wayland per-app profiles:

```bash
paru -S kdotool
```

After install:

```bash
# udev rules are installed by the package; reload happens in mouser.install
sudo /usr/share/mouser/install-linux-permissions.sh   # if HID access fails
reconnect Logitech receivers
mouser
```

## Package variants

### mouser-local (current tree)

```bash
cd /path/to/Mouser
paru -P ./packaging/aur/mouser-local
# or:
cd packaging/aur/mouser-local && makepkg -si
```

`pkgver` looks like `3.6.0.r1234.abc1234.local` (APP_VERSION + git revision).

### mouser-git (remote master)

Edit `mouser-git/PKGBUILD` `url=` if you build from a fork, then:

```bash
paru -P ./packaging/aur/mouser-git
```

### mouser (tagged release)

1. Sync pkgver from the app:

   ```bash
   ./packaging/aur/sync-pkgver.sh
   ```

2. Tag and push (upstream or your fork):

   ```bash
   git tag "v$(python -c 'from core.version import APP_VERSION; print(APP_VERSION)')"
   git push origin --tags
   ```

3. Build:

   ```bash
   paru -P ./packaging/aur/mouser
   ```

## Maintainer scripts

```bash
# Bump release PKGBUILD pkgver from core/version.py
./packaging/aur/sync-pkgver.sh

# Regenerate .SRCINFO (required before publishing to AUR)
./packaging/aur/regen-srcinfo.sh
```

## Publishing to AUR

Each of `mouser`, `mouser-git`, and `mouser-local` is a separate AUR package directory:

1. Clone `ssh://aur@aur.archlinux.org/<pkgname>.git`
2. Copy the matching `PKGBUILD`, `mouser.install` (as `mouser.install`), and `.SRCINFO`
3. For `mouser` / `mouser-git`, also copy `package-mouser.sh` reference or inline `package()` from `packaging/aur/package-mouser.sh`
4. `makepkg --printsrcinfo > .SRCINFO`
5. Commit and push to AUR

`mouser-local` is mainly for **local paru -P** workflows; publishing it to the public AUR is optional.

## Versioning model

| Layer | Source |
|-------|--------|
| App version | `core/version.py` → `APP_VERSION` (e.g. `3.6.0`) |
| Release `pkgver` | Same as `APP_VERSION`; `sync-pkgver.sh` updates `mouser/PKGBUILD` |
| Git packages | `git describe` when tags exist, else `APP_VERSION.r<rev>.<short>` |
| `pkgrel` | Bump manually on packaging-only fixes (same upstream version) |

The `/usr/bin/mouser` launcher exports `MOUSER_VERSION` so the UI matches the package version.

## What gets installed

- `/usr/bin/mouser` — launcher
- `/usr/lib/mouser/` — application source tree
- `/usr/share/applications/io.github.tombadash.mouser.desktop`
- `/usr/share/icons/hicolor/*/apps/io.github.tombadash.mouser.png`
- `/usr/lib/udev/rules.d/69-mouser-logitech.rules`
- `/usr/share/mouser/install-linux-permissions.sh`

User data: `~/.config/Mouser/config.json`, logs under `~/.local/state/Mouser/logs/`.

## More detail

See [BUILD_CACHYOS.md](../../BUILD_CACHYOS.md) for KDE Plasma / Wayland notes and hardware validation.