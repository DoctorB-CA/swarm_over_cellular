# Swarm Over Cellular - Setup Guide

This is a technical guide for setting up a drone swarm communication system using LTE cellular connectivity, WireGuard VPN, and BATMAN mesh networking.

## System Overview

- **King Drone (Drone 1)**: Gateway node with LTE modem (ppp0), provides internet to mesh via BATMAN
- **Normal Drones (Drone 2+)**: Client nodes connecting through BATMAN mesh
- **PC/Server**: Control station connected via WireGuard VPN

## Prerequisites

- Raspberry Pi boards (one per drone)
- SIMCom A7670E LTE modems
- Wi-Fi adapters for mesh networking
- Linux PC for control station

---

## Setup Steps

### 1. WireGuard VPN Configuration

Install and configure WireGuard for secure communication between PC and drones.

```bash
sudo apt install -y wireguard
```

Configuration files are provided in `wireguard_configuration/`:
- `server_conf.txt` - For VPN server
- `pc_conf.txt` - For control PC
- `king_drone_conf.txt` - For king drone (Drone 1)

Edit configuration:
```bash
sudo nano /etc/wireguard/wg0.conf
```

Start WireGuard:
```bash
sudo systemctl enable --now wg-quick@wg0
sudo systemctl status wg-quick@wg0
```

**Full instructions:** See [wireguard_configuration/wireguard_commands.md](wireguard_configuration/wireguard_commands.md)

---

### 2. Enable UART and PPP on Raspberry Pi

Configure serial port for A7670 LTE modem communication.

#### 2.1 Enable UART

```bash
sudo raspi-config
# Interface Options → Serial Port
# "Would you like a login shell accessible over serial?" → No
# "Would you like the serial port hardware enabled?" → Yes
sudo reboot
```

Serial port will be available at `/dev/serial0`.

**Full instructions:** See [pi  tutorials/enabling_serial_port.txt](pi  tutorials/enabling_serial_port.txt)

#### 2.2 Configure PPP

Install required packages:
```bash
sudo apt update
sudo apt install -y ppp minicom
```

Copy PPP configuration files from `ppp_confige/`:
```bash
sudo mkdir -p /etc/ppp/peers /etc/ppp_scripts
sudo cp ppp_confige/a7670-connect /etc/ppp_scripts/
sudo cp ppp_confige/a7670-disconnect /etc/ppp_scripts/
sudo cp ppp_confige/a7670 /etc/ppp/peers/
sudo chmod 600 /etc/ppp_scripts/a7670-*
```

Edit APN settings if needed:
```bash
sudo nano /etc/ppp_scripts/a7670-connect
# Find: OK 'AT+CGDCONT=1,"IP","net.hotm"'
# Replace with your carrier's APN
```

Enable PPP service:
```bash
sudo cp ppp_confige/ppp-a7670.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ppp-a7670.service
```

Verify PPP connection:
```bash
ip addr show ppp0
ping -I ppp0 -c 3 8.8.8.8
```

**Full instructions:** See [ppp_confige/README.md](ppp_confige/README.md)

**For higher bandwidth (required for video):** See [ppp_confige/higher_bandwidth/README.md](ppp_confige/higher_bandwidth/README.md)

---

### 3. Configure BATMAN Mesh Network

BATMAN-adv creates a mesh network over Wi-Fi for drone-to-drone communication.

#### 3.1 Install Dependencies

```bash
sudo apt install -y batctl iw nftables
```

#### 3.2 King Drone Setup (Drone 1)

The king drone acts as gateway providing internet to the mesh.

Copy script:
```bash
cp batman_configuration/start_mesh_king_drone.sh ~/
chmod +x ~/start_mesh_king_drone.sh
```

Test manually:
```bash
~/start_mesh_king_drone.sh
```

This script:
- Creates IBSS mesh on wlan0 (SSID: call-code-mesh)
- Sets up bat0 with IP 10.0.0.1/24
- Enables NAT from bat0 → ppp0 (LTE)
- Allows WireGuard (wg0) ↔ bat0 forwarding

#### 3.3 Normal Drone Setup (Drone 2+)

Client drones connect to the mesh and route through king drone.

Copy script:
```bash
cp batman_configuration/start_mesh_normanl_drone.sh ~/
chmod +x ~/start_mesh_normanl_drone.sh
```

Test manually (replace N with drone number 2-254):
```bash
~/start_mesh_normanl_drone.sh N
```

This script:
- Joins IBSS mesh on wlan0
- Sets up bat0 with IP 10.0.0.N/24
- Sets default route via 10.0.0.1 (king drone)

#### 3.4 Auto-start on Boot

Create systemd service (adjust paths as needed):
```bash
sudo nano /etc/systemd/system/mesh-drone.service
```

For king drone, use the service configuration from [batman_configuration/auto_run_batman.md](batman_configuration/auto_run_batman.md).

Enable service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now mesh-drone.service
```

Verify mesh:
```bash
sudo batctl o          # Show mesh neighbors
sudo batctl gwl        # Show gateway (on normal drones)
ip -br addr show bat0  # Verify IP
ping 10.0.0.1          # Ping king drone
```

**Full instructions:** See [batman_configuration/auto_run_batman.md](batman_configuration/auto_run_batman.md)

---

### 4. Upload Code and Verify

#### 4.1 Install Python Dependencies

Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

Install packages:
```bash
pip install -r requirements.txt
# Or manually:
pip install opencv-python numpy netifaces
```

**Full instructions:** See [pi  tutorials/creating_venv.md](pi  tutorials/creating_venv.md)

#### 4.2 Upload Code to Raspberry Pi

Copy files from `code/` directory to each Raspberry Pi:
- `pi.py` - Runs on Raspberry Pi, forwards commands to Tello drone
- `drone_translator.py` - Helper for drone communication
- `pc.py` - Runs on control PC

Transfer files:
```bash
scp code/pi.py code/drone_translator.py drone@<pi-ip>:~/
```

#### 4.3 Run and Test

On Raspberry Pi:
```bash
source venv/bin/activate
python3 pi.py
```

On PC:
```bash
python3 pc.py
```

The system will:
- Auto-detect drone number from bat0 IP (10.0.0.X → Drone X)
- Forward commands from PC to Tello drone
- Stream video back to PC

#### 4.4 Verification Checklist

1. **WireGuard**: `sudo wg show` - verify peers connected
2. **PPP**: `ip addr show ppp0` - verify LTE connection
3. **BATMAN**: `sudo batctl o` - verify mesh neighbors
4. **Network**: `ping 10.0.0.1` from normal drones
5. **Internet**: `ping -I bat0 8.8.8.8` from normal drones
6. **Code**: Run `pi.py` and verify no errors

---

## Network Topology

```
Internet
    |
[ppp0] - King Drone (10.0.0.1) - [wg0] - PC/Server
    |
[bat0 mesh]
    |
    +--- Normal Drone 2 (10.0.0.2)
    +--- Normal Drone 3 (10.0.0.3)
    +--- Normal Drone N (10.0.0.N)
```

---

## Troubleshooting

### PPP not connecting
```bash
sudo journalctl -u ppp-a7670.service -n 100
sudo minicom -D /dev/serial0 -b 115200  # Test modem with AT commands
```

### BATMAN mesh not forming
```bash
iw dev wlan0 info  # Verify IBSS mode
sudo batctl if     # Verify wlan0 attached to bat0
```

### No internet on normal drones
```bash
# On king drone:
sudo nft list table inet meshgw  # Verify NAT rules
# On normal drone:
ip route  # Verify default via 10.0.0.1
```

---

## File Structure

- `wireguard_configuration/` - VPN configuration files and commands
- `ppp_confige/` - LTE modem PPP setup
- `batman_configuration/` - Mesh network scripts
- `code/` - Python drone control code
- `pi  tutorials/` - Raspberry Pi configuration guides

---

## Notes

- Default mesh SSID: `call-code-mesh`
- Default mesh frequency: 2412 MHz (Channel 1)
- King drone must have working ppp0 before starting mesh
- Normal drones need only Wi-Fi adapter for mesh
