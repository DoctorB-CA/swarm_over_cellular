# A7670 UART 921600 Baud Patch (Boot-Safe)

## Background / Problem
The SIMCom A7670E LTE modem always boots with its UART set to **115200**.
Even if `AT+IPR=921600` is acknowledged, the baud rate often does **not persist**
across power cycles.

After reboot:
- PPP tries to open `/dev/serial0` at 921600
- Modem listens at 115200
- Result: service active, **no ppp0, no IP**

## The 3‑Player Model
UART works only if all three agree:
1. Raspberry Pi UART (`/dev/serial0`)
2. Program opening the port (`pppd`)
3. A7670E modem

At boot they do **not** agree → must be synchronized.

## Solution Overview
On every boot:
1. Start at 115200
2. Tell modem to switch to 921600
3. Switch Pi UART to 921600
4. Start PPP

## Files Added / Changed
- **Added:** `/usr/local/sbin/a7670_set_baud.sh`
- **Changed:** `/etc/ppp/peers/a7670` (baud → 921600)
- **Changed:** `ppp-a7670.service` (ExecStartPre)
- **Removed:** any `AT+IPR` from chat scripts
- **Removed:** any `stty` from systemd / rc.local

## Step 0 — One‑Time UART Clock Setup
Edit `/boot/firmware/config.txt`:
```
[all]
enable_uart=1
dtoverlay=disable-bt
init_uart_clock=14745600
```
Reboot.

## Step 1 — Baud Sync Script
Create `/usr/local/sbin/a7670_set_baud.sh`:
```
#!/usr/bin/env bash
set -e
DEV=/dev/serial0
LOW=115200
HIGH=921600
stty -F $DEV $LOW raw -echo -crtscts
printf 'AT\r' > $DEV
sleep 0.1
printf "AT+IPR=%d\r" "$HIGH" > $DEV
sleep 0.1
stty -F $DEV $HIGH raw -echo -crtscts
```
```
chmod +x /usr/local/sbin/a7670_set_baud.sh
```

## Step 2 — PPP Peer File
Edit `/etc/ppp/peers/a7670`:
```
/dev/serial0 921600
connect "/usr/sbin/chat -v -f /etc/ppp_scripts/a7670-connect"
disconnect "/usr/sbin/chat -v -f /etc/ppp_scripts/a7670-disconnect"
noauth
defaultroute
replacedefaultroute
usepeerdns
persist
nodetach
debug
local
lock
nobsdcomp
nodeflate
```

## Step 3 — Chat Script Rule
Ensure `/etc/ppp_scripts/a7670-connect`:
- DOES NOT contain `AT+IPR`
- Only modem init + dial

## Step 4 — systemd Service
Edit `/etc/systemd/system/ppp-a7670.service`:
```
[Unit]
Description=PPP over UART using SIMCom A7670 (baud patch)
After=dev-serial0.device network.target
Wants=dev-serial0.device

[Service]
Type=simple
ExecStartPre=/usr/local/sbin/a7670_set_baud.sh
ExecStart=/usr/sbin/pppd call a7670
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```
```
systemctl daemon-reload
systemctl enable --now ppp-a7670.service
```

## Verification
```
ip addr show ppp0
ping -I ppp0 -c 3 8.8.8.8
```

## Summary
BOOT → 115200 → AT+IPR=921600 → UART switch → PPP → IP
