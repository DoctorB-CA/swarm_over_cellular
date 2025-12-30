# Auto-start `start_mesh_normanl_drone.sh` on boot (systemd)

Target: **normal drone** Raspberry Pi  
User: **drone1** (home folder `~` → usually `/home/drone1`)  
Script location: `~/start_mesh_normanl_drone.sh` (already executable)

---

## 1) Confirm the script path + executable bit

```bash
echo $HOME
ls -l ~/start_mesh_normanl_drone.sh
chmod +x ~/start_mesh_normanl_drone.sh
```

You should see an `x` in the permissions (e.g., `-rwxr-xr-x`).

---

## 2) Create a systemd service file

Create:

```bash
sudo nano /etc/systemd/system/mesh-drone.service
```

Paste this:

```ini
[Unit]
Description=Start BATMAN mesh (normal drone)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/home/drone1/start_mesh_normanl_drone.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

> If your home is not `/home/drone1`, replace the `ExecStart=` path with the output of `echo $HOME`.

Save and exit.

---

## 3) Enable the service to run on boot + run it now

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now mesh-drone.service
```

---

## 4) Verify it worked

Status:

```bash
sudo systemctl status mesh-drone.service --no-pager
```

Logs from this boot:

```bash
sudo journalctl -u mesh-drone.service -b --no-pager
```

---

## 5) Common fixes (if it runs too early)

If Wi‑Fi isn’t ready when the script runs, add a short delay.

Edit the service:

```bash
sudo nano /etc/systemd/system/mesh-drone.service
```

Add this line under `[Service]` (before `ExecStart`):

```ini
ExecStartPre=/bin/sleep 5
```

Reload + restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart mesh-drone.service
```

---

## 6) Disable / stop later (optional)

Stop now:

```bash
sudo systemctl stop mesh-drone.service
```

Disable at boot:

```bash
sudo systemctl disable mesh-drone.service
```

Remove the service completely:

```bash
sudo rm /etc/systemd/system/mesh-drone.service
sudo systemctl daemon-reload
```
