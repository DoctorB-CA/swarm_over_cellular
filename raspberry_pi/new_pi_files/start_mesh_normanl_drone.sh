#!/bin/bash
set -euo pipefail

# ==========================================================
# DRONE 2/3/... ("Client") — Start IBSS + batman-adv
# - wlan0: IBSS mesh + batman-adv (bat0)
# - bat0: 10.0.0.<NODE_ID>/24
# - Default route: via 10.0.0.1 (Drone1 GW) on bat0
# ==========================================================

IFACE_MESH="${IFACE_MESH:-wlan0}"
IFACE_KEEP="${IFACE_KEEP:-wlan1}"     # optional; if absent, we won't touch it
SSID="${SSID:-call-code-mesh}"
FREQ_MHZ="${FREQ_MHZ:-2412}"
MTU="${MTU:-1468}"
GW_IP="${GW_IP:-10.0.0.1}"

# Node id from arg1 or NODE_ID env
NODE_ID="${1:-${NODE_ID:-}}"
if [[ -z "${NODE_ID}" ]]; then
  echo "Usage: $0 <NODE_ID 2-254>"
  echo "Example: $0 2   -> bat0 gets 10.0.0.2/24"
  exit 1
fi
if ! [[ "$NODE_ID" =~ ^[0-9]+$ ]] || (( NODE_ID < 2 || NODE_ID > 254 )); then
  echo "NODE_ID must be an integer 2..254 (GW is usually 1)"
  exit 1
fi
MESH_IP="10.0.0.${NODE_ID}/24"

log(){ echo "[*] $*"; }

# ---- sanity
ip link show "$IFACE_MESH" >/dev/null 2>&1 || { echo "No such iface: $IFACE_MESH"; exit 1; }
command -v iw     >/dev/null || { echo "Missing: iw     (sudo apt install -y iw)"; exit 1; }
command -v batctl >/dev/null || { echo "Missing: batctl (sudo apt install -y batctl)"; exit 1; }

# ---- detach wlan0 from managers (keep other ifaces untouched)
log "Detaching $IFACE_MESH from DHCP managers (keeping others untouched)..."
if command -v dhcpcd >/dev/null 2>&1; then
  sudo dhcpcd -k "$IFACE_MESH" 2>/dev/null || true
  sudo dhcpcd -x "$IFACE_MESH" 2>/dev/null || true
fi
if command -v nmcli >/dev/null 2>&1; then
  sudo nmcli dev set "$IFACE_MESH" managed no 2>/dev/null || true
fi

log "Stopping per-interface wpa_supplicant for $IFACE_MESH..."
sudo systemctl stop "wpa_supplicant@${IFACE_MESH}.service" 2>/dev/null || true
sudo pkill -f "wpa_supplicant.*-i${IFACE_MESH}\b" 2>/dev/null || true

log "Deleting Wi‑Fi Direct (P2P) virtual ifaces tied to $IFACE_MESH..."
for p2p in "p2p-dev-${IFACE_MESH}" "p2p-${IFACE_MESH}-0" "p2p-${IFACE_MESH}-1"; do
  sudo iw dev "$p2p" del 2>/dev/null || true
done

sudo rfkill unblock wifi 2>/dev/null || true

# ---- IBSS join
log "Switching $IFACE_MESH to IBSS and joining '$SSID' @ ${FREQ_MHZ}MHz..."
sudo ip link set dev "$IFACE_MESH" down
sudo iw dev "$IFACE_MESH" set type ibss
sudo ip link set dev "$IFACE_MESH" up
sudo iw dev "$IFACE_MESH" ibss join "$SSID" "$FREQ_MHZ" fixed-freq

# ---- batman
log "Loading batman-adv and attaching $IFACE_MESH -> bat0..."
sudo modprobe batman-adv
sudo batctl if add "$IFACE_MESH"
sudo ip link set dev bat0 up
sudo ip link set mtu "$MTU" dev bat0
sudo batctl gw_mode client

log "Assigning IP $MESH_IP to bat0..."
sudo ip addr flush dev bat0
sudo ip addr add "$MESH_IP" dev bat0

log "Setting default route via GW $GW_IP on bat0..."
sudo ip route replace default via "$GW_IP" dev bat0

log "DONE (Client)."
echo "  bat0: $MESH_IP"
echo "  default via: $GW_IP"
echo
echo "Verify:"
echo "  ip -br addr show bat0"
echo "  ip route"
echo "  sudo batctl o"
echo "  sudo batctl gwl"
