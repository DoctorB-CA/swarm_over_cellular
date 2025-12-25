#!/bin/bash
set -euo pipefail

# =========================
# IBSS + batman-adv setup (Raspberry Pi, using iw)
# =========================

IFACE="${IFACE:-wlan0}"
SSID="${SSID:-call-code-mesh}"
FREQ_MHZ="${FREQ_MHZ:-2412}"   # ch1=2412, ch6=2437, ch11=2462
MTU="${MTU:-1468}"
GW_MODE="${GW_MODE:-client}"   # client | server | off

log(){ echo "[*] $*"; }
warn(){ echo "[!] $*" >&2; }

# Basic sanity
if ! ip link show "$IFACE" >/dev/null 2>&1; then
  warn "Interface '$IFACE' not found. Run: iw dev"
  exit 1
fi
command -v iw >/dev/null || { warn "iw not found"; exit 1; }
command -v batctl >/dev/null || { warn "batctl not found (install: sudo apt install batctl)"; exit 1; }

log "Stopping Wi-Fi managers (ignore if not present)..."
sudo systemctl stop wpa_supplicant wpa_supplicant@"$IFACE" NetworkManager iwd systemd-networkd hostapd 2>/dev/null || true

log "Killing leftover processes that may hold the Wi-Fi phy..."
sudo killall wpa_supplicant 2>/dev/null || true
sudo killall iwd 2>/dev/null || true
sudo killall hostapd 2>/dev/null || true

log "Deleting Wi-Fi Direct (P2P) virtual interfaces if they exist..."
# Common names on Raspberry Pi / Linux
for p2p in "p2p-dev-$IFACE" "p2p-$IFACE-0" "p2p-$IFACE-1"; do
  sudo iw dev "$p2p" del 2>/dev/null || true
done

log "Unblocking Wi-Fi (rfkill)..."
sudo rfkill unblock wifi 2>/dev/null || true

log "Switching $IFACE to IBSS..."
sudo ip link set dev "$IFACE" down
sudo iw dev "$IFACE" set type ibss
sudo ip link set dev "$IFACE" up

log "Joining/creating IBSS '$SSID' @ ${FREQ_MHZ}MHz..."
sudo iw dev "$IFACE" ibss join "$SSID" "$FREQ_MHZ" fixed-freq

log "Loading batman-adv and attaching $IFACE..."
sudo modprobe batman-adv
sudo batctl if add "$IFACE"

log "Bringing up bat0 + setting MTU=${MTU}..."
sudo ip link set dev bat0 up
sudo ip link set mtu "$MTU" dev bat0

log "Setting batman gateway mode: $GW_MODE"
sudo batctl gw_mode "$GW_MODE"

log "Done."
log "Verify:"
echo "    iw dev $IFACE info | grep -i type"
echo "    sudo batctl if"
echo "    ip link show bat0"
