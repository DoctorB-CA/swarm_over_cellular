"""
Configuration file for Raspberry Pi Communication Bridge
This file contains Pi-specific network and operational settings
"""

# Network Interface Configuration
# These settings may need to be adjusted based on your Pi's network setup

# Cellular modem interface (adjust based on your setup)
CELLULAR_INTERFACE = "wwan0"      # Common for USB cellular modems
WIFI_INTERFACE = "wlan0"          # WiFi interface
ETHERNET_INTERFACE = "eth0"       # Ethernet interface

# Primary interface priority (bridge will try to use these in order)
INTERFACE_PRIORITY = [CELLULAR_INTERFACE, WIFI_INTERFACE, ETHERNET_INTERFACE]

# Network Configuration for Pi Bridge
# IP addresses that the Pi bridge will use
PI_BRIDGE_IP = "0.0.0.0"         # Listen on all interfaces
DRONE_LOCAL_IP = "192.168.1.100" # Local IP for direct drone connection
CONTROL_STATION_PUBLIC_IP = "10.0.0.3"  # Public IP of control station over cellular

# Port Configuration for Bridge
# These ports will be used by the Pi bridge to listen for drone communication
BRIDGE_COMMAND_PORT = 8889        # Listen for commands from control station
BRIDGE_TELEMETRY_PORT = 9888      # Listen for telemetry from drone
BRIDGE_VIDEO_PORT = 9890          # Listen for video from drone
BRIDGE_RTP_PORT = 6000            # Listen for RTP video from drone

# Forward to these ports on control station
CONTROL_COMMAND_PORT = 8889       # Forward commands to this port on control station
CONTROL_TELEMETRY_PORT = 8888     # Forward telemetry to this port on control station
CONTROL_VIDEO_PORT = 8890         # Forward video to this port on control station
CONTROL_RTP_PORT = 5000           # Forward RTP video to this port on control station

# Cellular Network Settings
CELLULAR_APN = "internet"         # Access Point Name for cellular connection
CELLULAR_USERNAME = ""            # Username for cellular connection (if required)
CELLULAR_PASSWORD = ""            # Password for cellular connection (if required)

# Bridge Operational Settings
BUFFER_SIZE = 65536               # Buffer size for socket operations
QUEUE_SIZE = 100                  # Maximum queue size for packet buffering
RETRY_ATTEMPTS = 3                # Number of retry attempts for failed operations
RETRY_DELAY = 1.0                 # Delay between retry attempts (seconds)

# Monitoring and Health Check
HEALTH_CHECK_INTERVAL = 30        # Health check interval in seconds
STATS_REPORT_INTERVAL = 60        # Statistics reporting interval in seconds
LOG_ROTATION_SIZE = 10485760      # Log file size before rotation (10MB)
MAX_LOG_FILES = 5                 # Maximum number of log files to keep

# Performance Tuning
THREAD_POOL_SIZE = 8              # Number of worker threads
SOCKET_BUFFER_SIZE = 262144       # Socket buffer size (256KB)
TCP_KEEPALIVE = True              # Enable TCP keepalive
UDP_CHECKSUM = True               # Enable UDP checksum verification

# Security Settings
ALLOWED_CONTROL_IPS = [           # List of allowed control station IPs
    "10.0.0.3",                   # Default control station IP
    "192.168.1.10",               # Backup control station IP
]

ENCRYPTION_ENABLED = False        # Enable/disable encryption (future feature)
AUTHENTICATION_ENABLED = False    # Enable/disable authentication (future feature)

# Failover and Redundancy
FAILOVER_ENABLED = True           # Enable automatic failover
FAILOVER_TIMEOUT = 30             # Failover timeout in seconds
BACKUP_CONTROL_STATION = "10.0.0.4"  # Backup control station IP
HEARTBEAT_INTERVAL = 10           # Heartbeat interval in seconds
HEARTBEAT_TIMEOUT = 30            # Heartbeat timeout in seconds

# System Resource Limits
MAX_MEMORY_USAGE = 512            # Maximum memory usage in MB
MAX_CPU_USAGE = 80                # Maximum CPU usage percentage
MAX_DISK_USAGE = 90               # Maximum disk usage percentage

# Debug and Development
DEBUG_MODE = False                # Enable debug mode
PACKET_LOGGING = False            # Log all packets (warning: generates large logs)
PERFORMANCE_MONITORING = True     # Enable performance monitoring
NETWORK_DIAGNOSTICS = True        # Enable network diagnostics

# Hardware-specific Settings
GPIO_STATUS_LED = 18              # GPIO pin for status LED (optional)
WATCHDOG_ENABLED = True           # Enable hardware watchdog
TEMPERATURE_MONITORING = True     # Monitor CPU temperature
TEMPERATURE_THRESHOLD = 70        # Temperature threshold in Celsius

# Bandwidth Management
BANDWIDTH_LIMIT_MBPS = 10         # Bandwidth limit in Mbps (for cellular)
VIDEO_QUALITY_AUTO_ADJUST = True  # Auto-adjust video quality based on bandwidth
MIN_VIDEO_QUALITY = 30            # Minimum video quality percentage
MAX_VIDEO_QUALITY = 90            # Maximum video quality percentage

# Error Handling
AUTO_RESTART_ON_ERROR = True      # Auto-restart on critical errors
MAX_RESTART_ATTEMPTS = 5          # Maximum restart attempts
RESTART_DELAY = 60                # Delay between restart attempts (seconds)
ERROR_REPORTING = True            # Enable error reporting
ERROR_LOG_LEVEL = "WARNING"       # Error log level

# Service Configuration
SERVICE_NAME = "drone-bridge"     # Service name for systemd
SERVICE_DESCRIPTION = "Drone Communication Bridge"
SERVICE_USER = "pi"               # User to run service as
SERVICE_GROUP = "pi"              # Group to run service as
WORKING_DIRECTORY = "/home/pi/drones_over_cellular/pi"
ENVIRONMENT_FILE = "/etc/default/drone-bridge"
