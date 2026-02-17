# A7670E USB High‑Speed Setup (ECM/RNDIS) for Raspberry Pi

Goal: move from **PPP over UART** (slow / CPU heavy) to **USB networking** (ECM recommended) so the Pi can carry higher throughput and keep **video at ~30 fps** reliably.

This bundle:
- disables the old PPP service
- initializes the modem for USB networking (ECM by default)
- brings up the USB network interface (dhcp)
- installs a systemd service so it starts automatically on boot
- optional udev rule to auto-start when you plug the modem

---

## 0) What changes?

**Old:** `pppd` over `/dev/serial0` at 115200  
**New:** USB network interface (usually `usb0` or `wwan0`) with DHCP

UART baud rate no longer matters for throughput.

---

## 1) Copy files

From this bundle:
- `a7670-usb.service`  → `/etc/systemd/system/a7670-usb.service`
- `a7670-usb-up.sh`   → `/usr/local/sbin/a7670-usb-up.sh`
- `a7670.env`         → `/etc/a7670.env`
- `99-a7670-usb.rules` (optional) → `/etc/udev/rules.d/99-a7670-usb.rules`

Commands:

```bash
sudo install -m 0644 a7670-usb.service /etc/systemd/system/a7670-usb.service
sudo install -m 0755 a7670-usb-up.sh /usr/local/sbin/a7670-usb-up.sh
sudo install -m 0644 a7670.env /etc/a7670.env

# optional
sudo install -m 0644 99-a7670-usb.rules /etc/udev/rules.d/99-a7670-usb.rules
```

---

## 2) Edit APN (VERY IMPORTANT)

Open:
```bash
sudo nano /etc/a7670.env
```

Set:
- `APN=...`  (example: `internet`, `net.hotm`, etc)
- Optionally `USB_MODE=ecm` or `USB_MODE=rndis`

---

## 3) Disable the old PPP service (so they don’t fight)

```bash
sudo systemctl disable --now ppp-a7670.service 2>/dev/null || true
sudo systemctl disable --now a7670.service 2>/dev/null || true
```

(If your PPP unit name is different, disable that one.)

---

## 4) Enable the new USB service

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now a7670-usb.service
```

Check status + logs:
```bash
systemctl status a7670-usb.service --no-pager
journalctl -u a7670-usb.service -f
```

---

## 5) Verify it works

### See USB serial ports and USB net interface
```bash
ls /dev/ttyUSB* 2>/dev/null
ip link | egrep "usb0|wwan0|enx"
```

### See IP and route
```bash
ip a show usb0 2>/dev/null || true
ip a show wwan0 2>/dev/null || true
ip route
```

### Ping test
```bash
ping -c 3 1.1.1.1
ping -c 3 google.com
```

---

## 6) Notes for 30 fps video

- For best video stability, avoid PPP.
- Use USB networking (ECM/RNDIS/QMI). This bundle uses **ECM by default**.
- Make sure the modem has good power (stable 5V, enough current) and a good LTE antenna.

---

## Troubleshooting

### Service says “No USB net interface”
Run:
```bash
dmesg | tail -n 100
lsusb
ip link
```
If you see the modem but no `usb0/wwan0`, try switching mode:

```bash
sudo sed -i 's/^USB_MODE=.*/USB_MODE=rndis/' /etc/a7670.env
sudo systemctl restart a7670-usb.service
```

### DNS doesn’t work
Check resolv:
```bash
cat /etc/resolv.conf
```

If needed (simple fix):
```bash
echo "nameserver 1.1.1.1" | sudo tee /etc/resolv.conf
```

### You want it to autostart when the modem is plugged in (hot-plug)
Install the udev rule in this bundle and reload rules:
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

---

## Files summary

- `a7670-usb-up.sh`  
  Initializes modem via AT on `/dev/ttyUSB2` (auto-detects best AT port), sets USB net mode (ECM/RNDIS), sets APN, enables data, then runs DHCP on the USB net interface.

- `a7670-usb.service`  
  Runs the script at boot and restarts on failure.

- `a7670.env`  
  Your APN + preferences (safe to edit).

- `99-a7670-usb.rules`  
  Optional: trigger service when modem appears.

