# A7670 PPP Setup (Raspberry Pi) — File Bundle

This bundle creates a PPP (ppp0) internet connection over a SIMCom A7670/A76xx LTE modem connected on UART **/dev/serial0** at **115200**.

It includes:
- Chat scripts: `a7670-connect`, `a7670-disconnect`
- PPP peer profile: `a7670`
- Optional systemd service: `ppp-a7670.service`
- Templates for PAP/CHAP secrets

---

## 0) Prerequisites

### Enable UART
Edit:
- `/boot/firmware/config.txt`

Ensure:
```
enable_uart=1
```

Reboot after changes:
```
sudo reboot
```

### Install packages
```
sudo apt update
sudo apt install -y ppp minicom
```

---

## 1) (Optional) Verify modem responds on UART

> IMPORTANT: only **one program** can use `/dev/serial0` at a time.
> Close minicom before starting PPP.

```
sudo minicom -D /dev/serial0 -b 115200
```
Type:
```
AT
```
Expect:
```
OK
```
Exit: `Ctrl-A`, then `X`, then `Yes`

---

## 2) Copy the provided files into place

From the folder where you extracted this bundle:

### Create directories
```
sudo mkdir -p /etc/ppp/peers
sudo mkdir -p /etc/ppp_scripts
```

### Copy chat scripts
```
sudo cp a7670-connect /etc/ppp_scripts/a7670-connect
sudo cp a7670-disconnect /etc/ppp_scripts/a7670-disconnect
sudo chmod 600 /etc/ppp_scripts/a7670-connect /etc/ppp_scripts/a7670-disconnect
```

### Copy PPP peer profile
```
sudo cp a7670 /etc/ppp/peers/a7670
```

---

## 3) Set APN (and optionally username/password)

### APN
Default APN in this bundle is:
- `net.hotm`

If you need a different APN, edit:
```
sudo nano /etc/ppp_scripts/a7670-connect
```
Find the line:
```
OK 'AT+CGDCONT=1,"IP","net.hotm"'
```
Replace `net.hotm` with your APN.

### PAP/CHAP credentials
Some carriers require PAP/CHAP user/pass (many do not). If needed, add entries.

Edit:
- `/etc/ppp/pap-secrets`
- `/etc/ppp/chap-secrets`

Append (example):
```
"bar" * "bar"
```

You can also change the `user` option in the peer file if required.

---

## 4) Start PPP

### Foreground (shows logs, occupies terminal)
```
sudo pppd call a7670
```

### Background (recommended if you have only one terminal)
```
sudo sh -c 'pppd call a7670 persist debug nodetach > /tmp/ppp.log 2>&1 &'
```

Check status:
```
ip addr show ppp0
ip route
tail -n 80 /tmp/ppp.log
```

Test connectivity through LTE explicitly:
```
ping -I ppp0 -c 3 8.8.8.8
curl --interface ppp0 -4 https://ifconfig.me
```

---

## 5) Stop PPP
```
sudo pkill pppd
```

---

## 6) (Optional) Auto-start PPP on boot using systemd

Copy the service file:
```
sudo cp ppp-a7670.service /etc/systemd/system/ppp-a7670.service
```

Enable + start:
```
sudo systemctl daemon-reload
sudo systemctl enable --now ppp-a7670.service
```

Check:
```
systemctl status ppp-a7670.service
journalctl -u ppp-a7670.service -n 200 --no-pager
```

Stop/disable:
```
sudo systemctl disable --now ppp-a7670.service
```

---

## Notes / Common gotchas

- If PPP “hangs” or chat fails, make sure **minicom is closed** and nothing else is using `/dev/serial0`.
- Your PPP IP will usually be a private address (10.x.x.x) — this is normal on cellular networks.
- If DNS works poorly, you can force DNS servers via `resolv.conf`/resolved, but generally `usepeerdns` is enough.

