# Shared package() implementation for Arch / CachyOS Mouser packages.
# Source this from PKGBUILD package() after cd "$srcdir/Mouser".

mouser_package() {
  local pkgroot="$1"
  local pkg_version="$2"

  install -dm755 "${pkgroot}/usr/lib/mouser"
  cp -r core ui images main_qml.py "${pkgroot}/usr/lib/mouser/"

  install -Dm644 LICENSE "${pkgroot}/usr/share/licenses/mouser/LICENSE"
  install -Dm644 README.md "${pkgroot}/usr/share/doc/mouser/README.md"
  install -Dm644 BUILD_CACHYOS.md "${pkgroot}/usr/share/doc/mouser/BUILD_CACHYOS.md"

  install -Dm644 packaging/linux/io.github.tombadash.mouser.desktop.in \
    "${pkgroot}/usr/share/applications/io.github.tombadash.mouser.desktop"
  sed -i \
    -e 's|@APP_NAME@|Mouser|g' \
    -e 's|@EXEC@|/usr/bin/mouser|g' \
    -e 's|@TRY_EXEC@|mouser|g' \
    -e 's|@ICON@|io.github.tombadash.mouser|g' \
    -e 's|@WORKDIR@||g' \
    -e 's|@SOURCE_PATH@||g' \
    -e '/@AUTOSTART_LINES@/d' \
    "${pkgroot}/usr/share/applications/io.github.tombadash.mouser.desktop"

  local icon_root="${pkgroot}/usr/share/icons/hicolor"
  local size dir icon_file
  for dir in packaging/linux/icons/hicolor/*/apps; do
    [[ -d "$dir" ]] || continue
    size=$(basename "$(dirname "$dir")")
    for icon_file in "$dir"/*.png; do
      [[ -f "$icon_file" ]] || continue
      install -Dm644 "$icon_file" \
        "${icon_root}/${size}/apps/$(basename "$icon_file")"
    done
  done

  install -Dm644 packaging/linux/69-mouser-logitech.rules \
    "${pkgroot}/usr/lib/udev/rules.d/69-mouser-logitech.rules"
  install -Dm644 packaging/linux/69-mouser-logitech.rules \
    "${pkgroot}/usr/share/mouser/69-mouser-logitech.rules"
  install -Dm755 packaging/linux/install-linux-permissions.sh \
    "${pkgroot}/usr/share/mouser/install-linux-permissions.sh"

  install -Dm755 /dev/stdin "${pkgroot}/usr/bin/mouser" <<EOF
#!/bin/bash
set -euo pipefail
MUSER_LIB="/usr/lib/mouser"
export PYTHONPATH="\${MUSER_LIB}\${PYTHONPATH:+:\${PYTHONPATH}}"
export MOUSER_VERSION="${pkg_version}"
cd "\${MUSER_LIB}"
exec /usr/bin/python main_qml.py "\$@"
EOF
}