#!/usr/bin/env bash
# wg_keys.sh — generate ONE WireGuard keypair (private + public)
# Creates exactly two files in the chosen directory:
#   private.key
#   public.key
#
# Usage:
#   ./wg_keys.sh                 # saves to ~/wireguard-keys
#   ./wg_keys.sh /etc/wireguard  # saves to /etc/wireguard (needs sudo)
#
set -euo pipefail

DIR="${1:-$HOME/wireguard-keys}"

if ! command -v wg >/dev/null 2>&1; then
  echo "ERROR: 'wg' not found. Install wireguard tools first (e.g. sudo apt install wireguard)." >&2
  exit 1
fi

mkdir -p "$DIR"
chmod 700 "$DIR" 2>/dev/null || true

PRIV="$DIR/private.key"
PUB="$DIR/public.key"

if [[ -f "$PRIV" || -f "$PUB" ]]; then
  echo "WARNING: $PRIV or $PUB already exists."
  read -r -p "Overwrite? [y/N]: " ans
  if [[ "${ans,,}" != "y" ]]; then
    echo "Aborted."
    exit 0
  fi
fi

umask 077
wg genkey | tee "$PRIV" | wg pubkey > "$PUB"
chmod 600 "$PRIV" "$PUB" 2>/dev/null || true

echo
echo "✅ WireGuard keypair generated."
echo "Saved files:"
echo "  Private key: $PRIV"
echo "  Public key : $PUB"
echo
echo "----- PUBLIC KEY -----"
cat "$PUB"
echo "----------------------"
echo
echo "----- PRIVATE KEY ----"
cat "$PRIV"
echo "----------------------"

