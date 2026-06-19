#!/usr/bin/env bash
# Sync packaging/aur/mouser/PKGBUILD pkgver with core/version.py APP_VERSION.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PKG_BUILD="${ROOT}/packaging/aur/mouser/PKGBUILD"

if [[ ! -f "$PKG_BUILD" ]]; then
  echo "Missing PKGBUILD: $PKG_BUILD" >&2
  exit 1
fi

VERSION="$(
  cd "$ROOT"
  /usr/bin/python -c 'from core.version import APP_VERSION; print(APP_VERSION)'
)"

if [[ ! "$VERSION" =~ ^[0-9]+(\.[0-9]+)*$ ]]; then
  echo "Unexpected APP_VERSION: $VERSION" >&2
  exit 1
fi

sed -i "s/^pkgver=.*/pkgver=${VERSION}/" "$PKG_BUILD"
echo "Updated ${PKG_BUILD} pkgver=${VERSION}"