"""
Central configuration file for network settings across all drone control applications.
Import this file in other Python files to ensure consistent network settings.
"""

# IP Addresses
DRONE_IP = "10.0.0.5"       # IP address of the drone/simulator
CONTROL_STATION_IP = "10.0.0.3"  # IP address of the control station

# Ports
COMMAND_PORT = 8889         # Port for sending commands to the drone
TELEMETRY_PORT = 8888       # Port for receiving telemetry from the drone
VIDEO_PORT = 8890           # Port for receiving video from the drone

# Timeouts
SOCKET_TIMEOUT = 1.0        # Socket timeout in seconds
TELEMETRY_INTERVAL = 0.5    # Interval between telemetry updates in seconds

# Protocol Constants
MAX_PACKET_SIZE = 1024      # Maximum packet size in bytes
