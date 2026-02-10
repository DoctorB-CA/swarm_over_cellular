# A7670 UART 921600 Baud Patch (Boot-Safe)

## Background / Problem

The SIMCom **A7670E** LTE modem always boots with its UART set to **115200**.  
Even if `AT+IPR=921600` is issued and acknowledged, the baud rate **does not persist**
across power cycles on many SIMCom firmwares.

This causes a failure on reboot when:

- `pppd` (or systemd service) opens `/dev/serial0` at **921600**
- the modem is still listening at **115200**
- the UART sides are misaligned

Result:
- `ppp0` never appears
- service is “active” but no IP address is assigned

---

## The Core Difficulty (3-Player Model)

For UART communication to work, **all three must agree on the baud rate**:

1. **Raspberry Pi UART driver** (`/dev/serial0`)
2. **Program opening the port** (`pppd`, `minicom`, etc.)
3. **A7670E modem UART**

At boot:
- modem starts at **115200**
- Pi + pppd expect **921600**

Jumping directly to 921600 fails.

---

## The Solution

Use a **deterministic 2-stage handshake on every boot**:

1. Start communication at **115200**
2. Tell the modem to switch to **921600** (`AT+IPR=921600`)
3. Immediately switch the Pi UART to **921600**
4. Only then start PPP

This aligns all three players reliably.

---

## What This Patch Adds / Changes

- ✅ Adds a **baud-sync pre-start script**
- ✅ Updates the PPP peer file to **921600**
- ✅ Simplifies the systemd service
- ❌ Removes baud handling from chat scripts
- ❌ Removes any `stty` logic from systemd or rc.local

---

## Step 0 — One-Time UART Clock Configuration (Required)

Edit:

```bash
sudo nano /boot/firmware/config.txt
