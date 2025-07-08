"""
Raspberry Pi Relay Configuration

This configuration file defines the network settings for the Raspberry Pi relay
that bridges communication between the base station and the drone.

Network topology:
Base Station <-> Raspberry Pi <-> Drone

The Raspberry Pi acts as a relay, forwarding:
- Commands from base station to drone
- Telemetry from drone to base station  
- Video stream from drone to base station
"""

# Network Interface Configuration
# ================================

# Base Station (Control Station) - where commands come from
BASE_STATION_IP = "10.0.0.3"       # IP address of the base station
BASE_STATION_COMMAND_PORT = 8889    # Port to receive commands from base station
BASE_STATION_TELEMETRY_PORT = 8888  # Port to send telemetry to base station
BASE_STATION_VIDEO_PORT = 5000      # Port to send RTP video to base station

# Drone - where commands are forwarded to
DRONE_IP = "192.168.10.1"              # IP address of the actual drone
DRONE_COMMAND_PORT = 8889           # Port to send commands to drone
DRONE_TELEMETRY_PORT = 8888         # Port to receive telemetry from drone
DRONE_VIDEO_PORT = 11111            # Port to receive video from drone

# Buffer and Performance Settings
# ===============================

BUFFER_SIZE = 4096              # Buffer size for UDP packets
SOCKET_TIMEOUT = 1.0            # Socket timeout in seconds
MAX_RETRIES = 3                 # Maximum retries for failed operations
KEEPALIVE_INTERVAL = 5.0        # Interval for keepalive messages in seconds

# Video Relay Settings
# ===================

VIDEO_BUFFER_SIZE = 65536       # Larger buffer for video data
VIDEO_FORWARD_THREADS = 2       # Number of threads for video forwarding
RTP_PACKET_SIZE = 1500          # Maximum RTP packet size

# Logging Configuration
# ====================

LOG_LEVEL = "INFO"              # Logging level: DEBUG, INFO, WARNING, ERROR
LOG_FILE = "/var/log/drone_relay.log"  # Log file path
ENABLE_PACKET_LOGGING = False   # Enable detailed packet logging (for debugging)

# Feature Flags
# =============

ENABLE_COMMAND_RELAY = True     # Enable command relay functionality
ENABLE_TELEMETRY_RELAY = True   # Enable telemetry relay functionality
ENABLE_VIDEO_RELAY = True       # Enable video relay functionality
ENABLE_HEARTBEAT = True         # Enable heartbeat/keepalive functionality

# Security Settings (for future enhancement)
# ==========================================

ENABLE_ENCRYPTION = False       # Enable packet encryption (not implemented yet)
ALLOWED_BASE_STATIONS = [       # Whitelist of allowed base station IPs
    "10.0.0.3",
    "10.0.0.5"  # Backup base station
]

# Network Interface Binding
# =========================

# Which interfaces to bind to (use "0.0.0.0" for all interfaces)
BIND_COMMAND_INTERFACE = "0.0.0.0"     # Interface for receiving commands
BIND_TELEMETRY_INTERFACE = "0.0.0.0"   # Interface for sending telemetry
BIND_VIDEO_INTERFACE = "0.0.0.0"       # Interface for video relay

# Advanced Settings
# ================

# Set to True to enable relay statistics and monitoring
ENABLE_STATISTICS = True

# Packet loss simulation for testing (percentage)
SIMULATE_PACKET_LOSS = 0  # 0-100, 0 means no simulation

# Quality of Service settings
COMMAND_PRIORITY = "high"    # Priority for command packets
TELEMETRY_PRIORITY = "medium"  # Priority for telemetry packets
VIDEO_PRIORITY = "low"       # Priority for video packets
