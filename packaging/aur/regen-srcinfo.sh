#!/usr/bin/env bash
# Regenerate .SRCINFO files for AUR / paru packages.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for pkg in mouser mouser-git mouser-local; do
  dir="${ROOT}/${pkg}"
  if [[ ! -f "${dir}/PKGBUILD" ]]; then
    continue
  fi
  echo "==> ${pkg}"
  (cd "$dir" && makepkg --printsrcinfo > .SRCINFO)
done

echo "Done. Commit updated .SRCINFO files when publishing to AUR."