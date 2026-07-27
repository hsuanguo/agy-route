#!/usr/bin/env bash
# install.sh — write the pinned `~/.local/bin/agy-bridge` shim for this plugin.
#
# The shim execs the absolute path of this repo's scripts/agy_bridge.sh recorded
# at install time. That means it does not glob the plugin cache per invocation
# and survives plugin upgrades (re-run install.sh to re-pin).
#
# Idempotent. Backs up any pre-existing non-symlink at the shim path.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRIDGE="$SCRIPT_DIR/agy_bridge.sh"
DEST_DIR="${AGY_BRIDGE_DEST_DIR:-$HOME/.local/bin}"
DEST="$DEST_DIR/agy-bridge"

if [[ ! -x "$BRIDGE" ]]; then
  echo "install.sh: bridge not found or not executable: $BRIDGE" >&2
  exit 1
fi
if [[ ! -r "$BRIDGE" ]]; then
  echo "install.sh: bridge not readable: $BRIDGE" >&2
  exit 1
fi

mkdir -p "$DEST_DIR"

# Backup any pre-existing shim (not our own).
if [[ -e "$DEST" || -L "$DEST" ]]; then
  if [[ -L "$DEST" ]] && readlink "$DEST" | grep -q "agy_bridge.sh"; then
    : # already pointing at this repo's bridge
  else
    ts="$(date +%Y%m%d-%H%M%S)"
    mv "$DEST" "$DEST.bak-agy-$ts"
    echo "install.sh: backed up existing $DEST -> $DEST.bak-agy-$ts" >&2
  fi
fi

cat > "$DEST" <<EOF
#!/usr/bin/env bash
# Pinned by agy-web-search plugin at $(date -Iseconds 2>/dev/null || date)
# Re-run the plugin's scripts/install.sh to re-pin after plugin updates.
exec "$BRIDGE" "\$@"
EOF
chmod 755 "$DEST"

# PATH nudge.
case ":$PATH:" in
  *":$DEST_DIR:"*) ;;
  *)
    echo "install.sh: $DEST_DIR is not on your PATH; add it (or symlink agy-bridge into a directory that is)." >&2
    ;;
esac

echo "installed: $DEST -> $BRIDGE"
echo "verify:     agy-bridge --types"
echo "help:       agy-bridge --help"