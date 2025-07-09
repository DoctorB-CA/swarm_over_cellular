#!/usr/bin/env python3
"""
Simple Drone Relay - Just forwards data between base station and drone
"""

import socket
import threading
import time
from relay_config import *

def forward_commands():
    """Forward commands: Base Station -> Drone"""
    # Listen for commands from base station
    cmd_in = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    cmd_in.bind(("0.0.0.0", BASE_STATION_COMMAND_PORT))
    
    # Send commands to drone
    cmd_out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    print(f"Command relay: {BASE_STATION_COMMAND_PORT} -> {DRONE_IP}:{DRONE_COMMAND_PORT}")
    
    while True:
        try:
            data, addr = cmd_in.recvfrom(1024)
            cmd_out.sendto(data, (DRONE_IP, DRONE_COMMAND_PORT))
            print(f"Command: {data.decode('utf-8', errors='ignore')}")
        except:
            pass

def forward_telemetry():
    """Forward telemetry: Drone -> Base Station"""
    # Listen for telemetry from drone
    tel_in = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    tel_in.bind(("0.0.0.0", DRONE_TELEMETRY_PORT))
    
    # Send telemetry to base station
    tel_out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    print(f"Telemetry relay: {DRONE_TELEMETRY_PORT} -> {BASE_STATION_IP}:{BASE_STATION_TELEMETRY_PORT}")
    
    while True:
        try:
            data, addr = tel_in.recvfrom(4096)
            tel_out.sendto(data, (BASE_STATION_IP, BASE_STATION_TELEMETRY_PORT))
            print(f"Telemetry: {len(data)} bytes")
        except:
            pass

def main():
    """Start simple relay"""
    print("Starting Simple Drone Relay...")
    print(f"Base Station: {BASE_STATION_IP}")
    print(f"Drone: {DRONE_IP}")
    
    # Start command forwarding
    cmd_thread = threading.Thread(target=forward_commands, daemon=True)
    cmd_thread.start()
    
    # Start telemetry forwarding  
    tel_thread = threading.Thread(target=forward_telemetry, daemon=True)
    tel_thread.start()
    
    print("Relay running... Press Ctrl+C to stop")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping relay...")

if __name__ == '__main__':
    main()
