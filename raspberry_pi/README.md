# Raspberry Pi Drone Communication Relay

This directory contains the complete Raspberry Pi relay system that bridges communication between a base station and a drone over cellular/different networks.

## Overview

The Raspberry Pi acts as a communication relay that:
- Forwards commands from the base station to the drone
- Relays telemetry data from the drone back to the base station
- Streams video from the drone to the base station using FFmpeg and RTP
- Provides network bridging between different network segments

## Files

### Core System
- `drone_relay.py` - Main relay application with multi-threaded communication handling
- `relay_config.py` - Configuration file for all network settings and relay parameters
- `setup_relay.sh` - Installation and setup script for the Raspberry Pi

### Network Configuration
- `network_config_tool.py` - Interactive tool for configuring network interfaces
- Helper scripts for network setup and WiFi hotspot configuration

### Testing and Monitoring
- `relay_test.py` - Test tool for simulating base station, drone, and monitoring relay

## Installation

1. Copy all files to your Raspberry Pi
2. Run the setup script as root:
   ```bash
   sudo bash setup_relay.sh
   ```

3. Configure network interfaces:
   ```bash
   sudo python3 network_config_tool.py
   ```

4. Edit the relay configuration if needed:
   ```bash
   ./edit_drone_config.sh
   ```

5. Start the relay service:
   ```bash
   ./start_drone_relay.sh
   ```

## Network Setup

### Typical Configuration

The relay is designed to work in a dual-network setup:

**Base Station Network (Wired - eth0):**
- Raspberry Pi: `10.0.0.4/24`
- Base Station: `10.0.0.3/24`
- Gateway: `10.0.0.1`

**Drone Network (WiFi Hotspot - wlan0):**
- Raspberry Pi: `192.168.4.1/24`
- Drone: `192.168.4.x/24` (assigned by DHCP)

### Quick Network Setup

Use the network configuration tool for easy setup:
```bash
sudo python3 network_config_tool.py
```

Select option 5 for quick setup with typical configuration.

## Configuration

Edit `/opt/drone_relay/relay_config.py` to customize:

### Key Settings
```python
# Base Station Network
BASE_STATION_IP = "10.0.0.3"
BASE_STATION_COMMAND_PORT = 8889
BASE_STATION_TELEMETRY_PORT = 8888
BASE_STATION_VIDEO_PORT = 5000

# Drone Network  
DRONE_IP = "10.0.0.5"  # Update this to match your drone
DRONE_COMMAND_PORT = 8889
DRONE_TELEMETRY_PORT = 8888
DRONE_VIDEO_PORT = 11111

# Feature Toggles
ENABLE_COMMAND_RELAY = True
ENABLE_TELEMETRY_RELAY = True
ENABLE_VIDEO_RELAY = True
```

## Usage

### Starting the Relay
```bash
# Start as a service (recommended)
./start_drone_relay.sh

# Or run directly for debugging
cd /opt/drone_relay
python3 drone_relay.py
```

### Monitoring
```bash
# Check service status
./check_drone_relay.sh

# View live logs
./view_drone_logs.sh

# Monitor network traffic
sudo iftop
sudo nethogs
```

### Testing

Test the relay with the included test tool:

```bash
# Test connectivity
python3 relay_test.py test

# Simulate base station commands
python3 relay_test.py base

# Simulate drone responses
python3 relay_test.py drone

# Monitor relay traffic
python3 relay_test.py monitor

# Full simulation (all components)
python3 relay_test.py full
```

## System Architecture

```
Base Station (10.0.0.3) <---> Raspberry Pi (10.0.0.4) <---> Drone (192.168.4.x)
                              │
                              ├── Command Relay (UDP 8889)
                              ├── Telemetry Relay (UDP 8888)  
                              └── Video Relay (FFmpeg RTP 5000 ← 11111)
```

### Communication Flow

1. **Commands**: Base Station → Relay → Drone
2. **Telemetry**: Drone → Relay → Base Station
3. **Video**: Drone → Relay (FFmpeg) → Base Station (RTP)

## Troubleshooting

### Common Issues

1. **Service won't start**
   ```bash
   # Check logs
   sudo journalctl -u drone-relay.service -f
   
   # Check configuration
   python3 -c "import relay_config; print('Config OK')"
   ```

2. **Network connectivity issues**
   ```bash
   # Check interfaces
   ip addr show
   
   # Test connectivity
   ping 10.0.0.3  # Base station
   ping 192.168.4.5  # Drone (if connected)
   ```

3. **Video relay problems**
   ```bash
   # Check FFmpeg
   which ffmpeg
   
   # Test manual video relay
   ffmpeg -f h264 -i udp://0.0.0.0:11111 -c copy -f rtp rtp://10.0.0.3:5000
   ```

4. **Port conflicts**
   ```bash
   # Check what's using ports
   sudo netstat -ulnp | grep -E "(8888|8889|5000|11111)"
   ```

### Log Files

- Service logs: `sudo journalctl -u drone-relay.service`
- Application logs: `/var/log/drone_relay.log`
- System logs: `/var/log/syslog`

## Security Considerations

- The relay includes basic IP whitelisting for base stations
- Consider setting up a VPN for additional security
- Use the firewall setup script: `./setup_firewall.sh`
- Disable unused services and ports

## Performance Tuning

For optimal performance:

1. **Network Buffers**: Increase UDP buffer sizes in configuration
2. **Video Quality**: Adjust video encoding settings on the drone
3. **CPU Priority**: Consider setting higher priority for the relay process
4. **Network QoS**: Configure Quality of Service rules for different traffic types

## Advanced Features

### Statistics and Monitoring
The relay provides real-time statistics including:
- Commands forwarded
- Telemetry packets relayed
- Video bytes transferred
- Error counts
- Uptime and performance metrics

### Heartbeat System
Automatic heartbeat messages to the base station include:
- Relay status
- Performance statistics
- Network health information

### Multi-Interface Support
The relay can handle multiple network interfaces and route traffic appropriately based on configuration.

## Integration

This relay is designed to work with:
- The base station GUI application
- Standard drone protocols (Tello SDK, MAVLink, etc.)
- Any system using UDP for drone communication

The configuration is compatible with the base station's `network_config.py` settings.
