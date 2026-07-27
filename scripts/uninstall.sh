#!/usr/bin/env bash
# uninstall.sh — remove the pinned `~/.local/bin/agy-bridge` shim written by
# scripts/install.sh. Idempotent. Does NOT delete backups; does NOT delete the
# model-resolution cache (~/.cache/agy-bridge-models) — remove that manually if
# desired.
set -euo pipefail

DEST_DIR="${AGY_BRIDGE_DEST_DIR:-$HOME/.local/bin}"
DEST="$DEST_DIR/agy-bridge"

if [[ ! -e "$DEST" && ! -L "$DEST" ]]; then
  echo "uninstall.sh: no shim at $DEST (nothing to do)"
  exit 0
fi

# Refuse to delete anything we didn't write.
if [[ -L "$DEST" ]]; then
  target="$(readlink "$DEST" 2>/dev/null || true)"
  if [[ "$target" != *"agy_bridge.sh" ]]; then
    echo "uninstall.sh: $DEST is a symlink to $target — refusing to delete (not ours)" >&2
    exit 1
  fi
  rm "$DEST"
  echo "removed symlink: $DEST"
elif [[ -f "$DEST" ]]; then
  if ! grep -q "Pinned by agy-web-search plugin" "$DEST"; then
    echo "uninstall.sh: $DEST is a regular file not written by this plugin — refusing" >&2
    exit 1
  fi
  rm "$DEST"
  echo "removed shim: $DEST"
fi

echo "verify:     agy-bridge --types  # should now fail with command-not-found"