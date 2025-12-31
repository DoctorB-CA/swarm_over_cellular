#!/bin/bash
set -euo pipefail

# ==========================================================
# DRONE 1 ("King") — Start IBSS + batman-adv AND become GW
# - wlan0: IBSS mesh + batman-adv (bat0)
# - ppp0/wlan1: stays normal (internet uplink via DHCP / NetworkManager / etc)
# - bat0: 10.0.0.1/24
# - NAT:  bat0 -> ppp0/wlan1 (nftables)
# - VPN:  allow forwarding between wg0 <-> bat0 (so PC can reach mesh)
# ==========================================================

# ---- fixed config (edit only if your names differ)
IFACE_MESH="${IFACE_MESH:-wlan0}"
#IFACE_UPLINK="${IFACE_UPLINK:-wlan1}"  <- if you using wlan1 and not cellular (ppp0)
IFACE_UPLINK="${IFACE_UPLINK:-ppp0}"
IFACE_WG="${IFACE_WG:-wg0}"

SSID="${SSID:-call-code-mesh}"
FREQ_MHZ="${FREQ_MHZ:-2412}"          # ch1=2412, ch6=2437, ch11=2462
MTU="${MTU:-1468}"
GW_IP_CIDR="${GW_IP_CIDR:-10.0.0.1/24}"
GW_BW="${GW_BW:-5mbit/1mbit}"         # advertised bandwidth hint for batman gw_mode server

log(){ echo "[*] $*"; }

# ---- sanity
ip link show "$IFACE_MESH"   >/dev/null 2>&1 || { echo "No such iface: $IFACE_MESH"; exit 1; }
ip link show "$IFACE_UPLINK" >/dev/null 2>&1 || { echo "No such iface: $IFACE_UPLINK"; exit 1; }
command -v iw      >/dev/null || { echo "Missing: iw      (sudo apt install -y iw)"; exit 1; }
command -v batctl  >/dev/null || { echo "Missing: batctl  (sudo apt install -y batctl)"; exit 1; }
command -v nft     >/dev/null || { echo "Missing: nft     (sudo apt install -y nftables)"; exit 1; }

# ---- keep uplink alive (ppp0/wlan1), detach only wlan0 from managers
log "Detaching $IFACE_MESH from DHCP managers (keeping $IFACE_UPLINK untouched)..."
if command -v dhcpcd >/dev/null 2>&1; then
  sudo dhcpcd -k "$IFACE_MESH" 2>/dev/null || true
  sudo dhcpcd -x "$IFACE_MESH" 2>/dev/null || true
fi

log "If NetworkManager exists: mark $IFACE_MESH unmanaged (does not affect $IFACE_UPLINK)..."
if command -v nmcli >/dev/null 2>&1; then
  sudo nmcli dev set "$IFACE_MESH" managed no 2>/dev/null || true
fi

log "Stopping per-interface wpa_supplicant for $IFACE_MESH (leave others running)..."
sudo systemctl stop "wpa_supplicant@${IFACE_MESH}.service" 2>/dev/null || true
sudo pkill -f "wpa_supplicant.*-i${IFACE_MESH}\b" 2>/dev/null || true

log "Deleting Wi‑Fi Direct (P2P) virtual ifaces tied to $IFACE_MESH (common -16 busy cause)..."
for p2p in "p2p-dev-${IFACE_MESH}" "p2p-${IFACE_MESH}-0" "p2p-${IFACE_MESH}-1"; do
  sudo iw dev "$p2p" del 2>/dev/null || true
done

log "Unblocking Wi‑Fi (rfkill) ..."
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

log "Assigning gateway IP $GW_IP_CIDR to bat0..."
sudo ip addr flush dev bat0
sudo ip addr add "$GW_IP_CIDR" dev bat0

log "Announcing this node as batman GW (gw_mode server $GW_BW)..."
sudo batctl meshif bat0 gw_mode server "$GW_BW"

# ---- kernel forwarding
log "Enabling IPv4 forwarding..."
sudo sysctl -w net.ipv4.ip_forward=1 >/dev/null

# ---- NAT + forward rules (nftables)
log "Configuring nftables NAT + forwarding (bat0 -> $IFACE_UPLINK)..."
sudo nft delete table inet meshgw 2>/dev/null || true
sudo nft add table inet meshgw

sudo nft add chain inet meshgw forward '{ type filter hook forward priority 0; policy drop; }'
sudo nft add rule  inet meshgw forward iifname "bat0" oifname "$IFACE_UPLINK" accept
sudo nft add rule  inet meshgw forward iifname "$IFACE_UPLINK" oifname "bat0" ct state established,related accept

# ---- VPN <-> Mesh forwarding (optional)
# If wg0 exists, allow wg0 <-> bat0 so your PC (over VPN) can reach mesh nodes.
if ip link show "$IFACE_WG" >/dev/null 2>&1; then
  log "wg interface $IFACE_WG detected: allowing $IFACE_WG <-> bat0 forwarding..."
  sudo nft add rule inet meshgw forward iifname "$IFACE_WG" oifname "bat0" accept
  sudo nft add rule inet meshgw forward iifname "bat0" oifname "$IFACE_WG" accept
else
  log "wg interface $IFACE_WG not found (skipping VPN<->mesh forward rules)."
fi

sudo nft add chain inet meshgw postrouting '{ type nat hook postrouting priority srcnat; }'
sudo nft add rule  inet meshgw postrouting oifname "$IFACE_UPLINK" masquerade

log "DONE (King GW)."
echo "  Mesh:    $SSID @ ${FREQ_MHZ}MHz on $IFACE_MESH"
echo "  bat0:    $GW_IP_CIDR"
echo "  Uplink:  $IFACE_UPLINK (must have real internet)"
echo "  VPN IF:  $IFACE_WG (forwarding to mesh if present)"
echo
echo "Verify:"
echo "  iw dev $IFACE_MESH info | grep -i type"
echo "  ip -br addr show bat0 $IFACE_UPLINK"
echo "  sudo nft list table inet meshgw"
echo "  sudo batctl o"
echo "  sudo batctl gwl"
