#!/usr/bin/env bash
set -euo pipefail

DEV="/dev/serial0"
LOW=115200
HIGH=921600

# Ensure port exists
[ -e "$DEV" ] || { echo "ERR: $DEV not found"; exit 1; }

# 1) Configure host UART to LOW and talk to modem
stty -F "$DEV" $LOW raw -echo -echoe -echok -crtscts

# Flush any junk
dd if="$DEV" of=/dev/null bs=256 count=1 status=none || true

# 2) Ask modem to switch to HIGH
# IMPORTANT: \r is required (carriage return)
printf 'AT\r' > "$DEV"
sleep 0.1
printf "AT+IPR=%d\r" "$HIGH" > "$DEV"
sleep 0.1

# 3) Immediately switch host UART to HIGH
stty -F "$DEV" $HIGH raw -echo -echoe -echok -crtscts
sleep 0.1

# 4) Quick sanity ping at HIGH (optional)
printf 'AT\r' > "$DEV"
sleep 0.2

exit 0
