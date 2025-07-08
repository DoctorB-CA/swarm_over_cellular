# Drone Communication Bridge for Raspberry Pi

This directory contains the communication bridge software that runs on a Raspberry Pi to relay communication between a drone and a control station over a cellular network.

## Overview

The communication bridge acts as a transparent proxy, forwarding:
- Commands from control station to drone
- Telemetry from drone to control station  
- Video streams (both legacy and RTP) from drone to control station

## Files

- `communication_bridge.py` - Main bridge application
- `bridge_config.py` - Configuration settings for the Pi environment
- `run_bridge.sh` - Startup/management script
- `drone-bridge.service` - Systemd service file for automatic startup
- `README.md` - This file

## Setup Instructions

### 1. Hardware Requirements

- Raspberry Pi 4 (recommended) or Pi 3B+
- MicroSD card (32GB+ recommended)
- USB cellular modem or Pi HAT with cellular connectivity
- Power supply (consider UPS for drone applications)

### 2. Software Prerequisites

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python dependencies
sudo apt install -y python3 python3-pip python3-venv

# Install system dependencies
sudo apt install -y git wget curl
```

### 3. Network Configuration

#### Cellular Modem Setup

Configure your cellular modem according to manufacturer instructions. Common steps:

```bash
# Install modem utilities
sudo apt install -y modemmanager network-manager

# Check modem detection
mmcli -L

# Configure APN (example for generic internet APN)
sudo nmcli connection add type gsm ifname '*' con-name cellular apn internet
sudo nmcli connection up cellular
```

#### Network Interfaces

Edit `/etc/dhcpcd.conf` or use NetworkManager to configure static IPs if needed:

```bash
# Example static IP configuration
interface wlan0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8 8.8.4.4
```

### 4. Install Bridge Software

```bash
# Clone the project (if not already present)
cd /home/pi
git clone <repository-url> drones_over_cellular
cd drones_over_cellular/pi

# Make scripts executable
chmod +x communication_bridge.py
chmod +x run_bridge.sh

# Test the bridge
python3 communication_bridge.py --help
```

### 5. Configuration

Edit `bridge_config.py` to match your network setup:

```python
# Update these settings for your environment
CONTROL_STATION_PUBLIC_IP = "your.control.station.ip"
CELLULAR_APN = "your.cellular.apn"
DRONE_LOCAL_IP = "192.168.1.100"  # Direct connection to drone
```

### 6. Install as System Service

```bash
# Copy service file
sudo cp drone-bridge.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service for automatic startup
sudo systemctl enable drone-bridge

# Start service
sudo systemctl start drone-bridge

# Check status
sudo systemctl status drone-bridge
```

## Usage

### Manual Operation

```bash
# Start bridge
./run_bridge.sh start

# Check status
./run_bridge.sh status

# Stop bridge
./run_bridge.sh stop

# Restart bridge
./run_bridge.sh restart
```

### Service Operation

```bash
# Start service
sudo systemctl start drone-bridge

# Stop service
sudo systemctl stop drone-bridge

# Restart service
sudo systemctl restart drone-bridge

# View logs
sudo journalctl -u drone-bridge -f
```

### Command Line Options

```bash
python3 communication_bridge.py --help

# Example with custom settings
python3 communication_bridge.py \
    --drone-ip 192.168.1.100 \
    --control-ip 10.0.0.3 \
    --verbose
```

## Monitoring

### Log Files

- `/tmp/communication_bridge.log` - Main application log
- `/tmp/bridge_startup.log` - Startup script log
- `sudo journalctl -u drone-bridge` - Systemd service logs

### Statistics

The bridge reports statistics every 60 seconds including:
- Commands relayed
- Telemetry packets relayed
- Video packets relayed
- Connection status
- Error counts

### Health Monitoring

```bash
# Check system resources
top
htop
iotop

# Check network connectivity
ping google.com
ping <control-station-ip>
ping <drone-ip>

# Check cellular connection
mmcli -m 0 --simple-status

# Check interface status
ip addr show
iwconfig
```

## Troubleshooting

### Common Issues

1. **Bridge won't start**
   - Check network configuration
   - Verify Python dependencies
   - Check firewall settings
   - Review logs for error messages

2. **No communication with drone**
   - Verify drone IP address
   - Check local network connectivity
   - Ensure drone is in the correct mode
   - Check port configurations

3. **No communication with control station**
   - Verify cellular connection
   - Check control station IP and ports
   - Test internet connectivity
   - Check NAT/firewall settings

4. **High latency or packet loss**
   - Monitor cellular signal strength
   - Check bandwidth usage
   - Adjust video quality settings
   - Consider network optimization

### Debug Mode

```bash
# Run with debug output
python3 communication_bridge.py --verbose

# Enable packet logging (warning: large logs)
# Edit bridge_config.py: PACKET_LOGGING = True
```

### Network Diagnostics

```bash
# Test ports
nmap -p 8889,8888,8890,5000 <control-station-ip>
nmap -p 8889,8888,8890,5000 <drone-ip>

# Monitor traffic
sudo tcpdump -i any port 8889
sudo netstat -tulpn | grep python

# Check routing
ip route show
traceroute <control-station-ip>
```

## Security Considerations

1. **Network Security**
   - Use VPN when possible
   - Configure firewalls appropriately
   - Monitor for unauthorized access

2. **Physical Security**
   - Secure Pi mounting in drone
   - Protect against vibration/moisture
   - Consider tamper detection

3. **Data Security**
   - Consider encryption for sensitive operations
   - Implement authentication if required
   - Monitor for data integrity

## Performance Optimization

1. **Network Optimization**
   - Adjust buffer sizes in configuration
   - Monitor bandwidth usage
   - Implement QoS if possible

2. **System Optimization**
   - Disable unnecessary services
   - Optimize Pi for real-time operation
   - Monitor system resources

3. **Video Optimization**
   - Adjust video quality based on bandwidth
   - Use appropriate codecs
   - Implement adaptive streaming

## Maintenance

### Regular Tasks

1. **System Updates**
   ```bash
   sudo apt update && sudo apt upgrade
   ```

2. **Log Rotation**
   ```bash
   # Configure logrotate for bridge logs
   sudo nano /etc/logrotate.d/drone-bridge
   ```

3. **Backup Configuration**
   ```bash
   # Backup configuration files
   tar -czf drone-bridge-backup.tar.gz *.py *.sh *.service
   ```

### Monitoring Scripts

Consider setting up automated monitoring for:
- Service health
- Network connectivity
- System resources
- Error rates

## Support

For issues and support:
1. Check the logs for error messages
2. Verify network configuration
3. Test individual components
4. Review this documentation
5. Create detailed issue reports

## Development

### Testing

```bash
# Test individual components
python3 -c "from communication_bridge import CommunicationBridge; print('Import OK')"

# Test network connectivity
python3 -c "import socket; socket.create_connection(('google.com', 80), timeout=5)"
```

### Extending

The bridge is designed to be modular. You can extend it by:
- Adding new relay protocols
- Implementing encryption
- Adding authentication
- Enhancing monitoring
- Implementing failover mechanisms
