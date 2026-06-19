#!/bin/sh
set -eu

RULE_NAME="69-mouser-logitech.rules"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SCRIPT_PATH="$SCRIPT_DIR/$(basename -- "$0")"
RULE_TARGET="/etc/udev/rules.d/$RULE_NAME"
PACKAGED_RULE="/usr/lib/udev/rules.d/$RULE_NAME"

_resolve_rule_source() {
  for candidate in \
    "$SCRIPT_DIR/$RULE_NAME" \
    "/usr/share/mouser/$RULE_NAME"
  do
    if [ -f "$candidate" ]; then
      printf '%s' "$candidate"
      return 0
    fi
  done
  return 1
}

_reload_udev() {
  if command -v modprobe >/dev/null 2>&1; then
    modprobe uinput 2>/dev/null || true
  fi
  if command -v udevadm >/dev/null 2>&1; then
    udevadm control --reload-rules
    udevadm trigger
    udevadm settle 2>/dev/null || true
  else
    echo "udevadm was not found; could not reload udev." >&2
    return 1
  fi
}

if [ "$(id -u)" -ne 0 ]; then
  if command -v pkexec >/dev/null 2>&1; then
    exec pkexec /bin/sh "$SCRIPT_PATH"
  fi
  if command -v sudo >/dev/null 2>&1; then
    exec sudo /bin/sh "$SCRIPT_PATH"
  fi
  echo "This installer needs administrator privileges." >&2
  echo "Run: sudo /bin/sh \"$SCRIPT_PATH\"" >&2
  exit 1
fi

if [ -f "$PACKAGED_RULE" ]; then
  echo "udev rule already installed by package: $PACKAGED_RULE"
  _reload_udev
  echo "Reconnect your Logitech devices, fully quit Mouser, then launch Mouser again."
  exit 0
fi

RULE_SOURCE="$(_resolve_rule_source || true)"
if [ -z "$RULE_SOURCE" ]; then
  echo "Missing udev rule file. Expected one of:" >&2
  echo "  $SCRIPT_DIR/$RULE_NAME" >&2
  echo "  /usr/share/mouser/$RULE_NAME" >&2
  echo "  $PACKAGED_RULE (via pacman/paru package)" >&2
  exit 1
fi

install -m 0644 "$RULE_SOURCE" "$RULE_TARGET"
_reload_udev

echo "Installed $RULE_TARGET"
echo "Reconnect your Logitech mouse, fully quit Mouser, then launch Mouser again."
echo "If desktop launch still cannot access the mouse, log out and back in once."