#!/usr/bin/env bash
set -euo pipefail

# Load env if not already loaded by systemd (safe)
ENV_FILE="/etc/a7670.env"
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

APN="${APN:-internet}"
USB_MODE="${USB_MODE:-ecm}"      # ecm|rndis|auto
USBNETIP="${USBNETIP:-0}"        # 0 private, 1 public
FORCE_CFUN="${FORCE_CFUN:-1}"

log(){ echo "[a7670-usb] $*"; }

# Pick an AT port. Many SIMCom expose multiple /dev/ttyUSB*; one is AT.
pick_at_port() {
  for p in /dev/ttyUSB*; do
    [[ -e "$p" ]] || continue
    # Try AT quickly
    if timeout 1 bash -c "printf 'AT\r' > $p" 2>/dev/null; then
      # Read response
      local resp
      resp="$(timeout 1 cat "$p" 2>/dev/null | tr -d '\r' | tail -n +1 | head -n 5 || true)"
      if echo "$resp" | grep -q "OK"; then
        echo "$p"
        return 0
      fi
    fi
  done
  return 1
}

AT_PORT="$(pick_at_port || true)"
if [[ -z "${AT_PORT}" ]]; then
  # fallback: common AT port is ttyUSB2
  AT_PORT="/dev/ttyUSB2"
fi
log "Using AT port: ${AT_PORT}"

# Send an AT command and wait for OK/ERROR
at() {
  local cmd="$1"
  log "AT> $cmd"
  # write
  printf "%s\r" "$cmd" > "$AT_PORT"
  # read up to 2 seconds
  local out
  out="$(timeout 2 cat "$AT_PORT" 2>/dev/null | tr -d '\r' | head -n 20 || true)"
  echo "$out" | sed 's/^/[a7670-usb] AT< /'
  if echo "$out" | grep -q "^OK"; then
    return 0
  fi
  if echo "$out" | grep -q "ERROR"; then
    return 1
  fi
  # Some commands respond with data then OK; accept if OK is present anywhere
  if echo "$out" | grep -q "OK"; then
    return 0
  fi
  return 0
}

# Basic sanity
at "ATE0" || true
at "AT+CPIN?" || true

# Ensure RF on
if [[ "$FORCE_CFUN" == "1" ]]; then
  at "AT+CFUN=1" || true
fi

# Set APN for profile 1
at "AT+CGDCONT=1,\"IP\",\"${APN}\"" || true

# Choose USB net mode (persistent)
case "${USB_MODE}" in
  ecm)
    # 1 = ECM
    at "AT\$MYCONFIG=\"USBNETMODE\",1" || true
    ;;
  rndis)
    # 0 = RNDIS
    at "AT\$MYCONFIG=\"USBNETMODE\",0" || true
    ;;
  auto)
    # 2 = AUTO
    at "AT\$MYCONFIG=\"USBNETMODE\",2" || true
    ;;
  *)
    log "Unknown USB_MODE=${USB_MODE}, keeping current"
    ;;
esac

# Select private/public IP behavior on USB net (persistent)
at "AT+USBNETIP=${USBNETIP}" || true

# Enable USBNET dial mode (persistent) - if supported on your firmware
# 1 = USBNET (some firmwares use different values; script continues even if ERROR)
at "AT+DIALMODE=1" || true

# Wait for the USB network interface to appear
log "Waiting for USB net interface (usb0/wwan0/enx*)..."
for i in {1..30}; do
  IFACE="$(ip -o link show | awk -F': ' '{print $2}' | egrep '^(usb0|wwan0|enx)' | head -n1 || true)"
  if [[ -n "${IFACE}" ]]; then
    log "Found interface: ${IFACE}"
    break
  fi
  sleep 1
done

IFACE="${IFACE:-}"
if [[ -z "${IFACE}" ]]; then
  log "ERROR: No USB net interface appeared. Check dmesg/lsusb."
  exit 1
fi

# Bring it up
ip link set "${IFACE}" up || true

# DHCP client (use whichever exists)
log "Requesting DHCP on ${IFACE}..."
if command -v dhclient >/dev/null 2>&1; then
  dhclient -v -1 "${IFACE}" || true
elif command -v udhcpc >/dev/null 2>&1; then
  udhcpc -i "${IFACE}" -q -n || true
else
  log "No dhclient/udhcpc found. Install one: sudo apt install isc-dhcp-client"
  exit 1
fi

log "Done. Current IP + route:"
ip a show "${IFACE}" || true
ip route || true
