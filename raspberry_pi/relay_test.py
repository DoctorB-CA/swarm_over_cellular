#!/usr/bin/env python3
"""
Drone Relay Test and Monitoring Tool

This tool helps test and monitor the drone relay system.
It can simulate base station commands and drone responses for testing.
"""

import socket
import threading
import time
import json
import argparse
from datetime import datetime
import sys

class RelayTester:
    """Test tool for the drone relay system"""
    
    def __init__(self):
        self.running = False
        self.base_station_ip = "10.0.0.3"
        self.relay_ip = "10.0.0.4"
        self.drone_ip = "10.0.0.5"
        
        # Ports
        self.command_port = 8889
        self.telemetry_port = 8888
        self.video_port = 5000
    
    def simulate_base_station(self):
        """Simulate base station sending commands"""
        print("Starting base station simulator...")
        
        command_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        commands = [
            "command",
            "takeoff",
            "up 50",
            "forward 100",
            "cw 90",
            "land"
        ]
        
        command_index = 0
        
        while self.running:
            try:
                # Send command to relay
                command = commands[command_index % len(commands)]
                command_socket.sendto(
                    command.encode('utf-8'),
                    (self.relay_ip, self.command_port)
                )
                
                print(f"[BASE] Sent command: {command}")
                command_index += 1
                
                time.sleep(3)
                
            except Exception as e:
                print(f"[BASE] Error: {e}")
                break
        
        command_socket.close()
        print("[BASE] Base station simulator stopped")
    
    def simulate_drone(self):
        """Simulate drone sending telemetry"""
        print("Starting drone simulator...")
        
        # Telemetry socket
        telemetry_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Command receiver socket
        command_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        command_socket.bind(("0.0.0.0", self.command_port))
        command_socket.settimeout(1.0)
        
        # Start command receiver thread
        def command_receiver():
            while self.running:
                try:
                    data, addr = command_socket.recvfrom(1024)
                    command = data.decode('utf-8')
                    print(f"[DRONE] Received command from {addr}: {command}")
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"[DRONE] Command receiver error: {e}")
        
        cmd_thread = threading.Thread(target=command_receiver)
        cmd_thread.daemon = True
        cmd_thread.start()
        
        # Send telemetry
        telemetry_count = 0
        while self.running:
            try:
                # Create telemetry data
                telemetry = {
                    "battery": 85 - (telemetry_count % 20),
                    "altitude": 10 + (telemetry_count % 5),
                    "speed": 2.5,
                    "temperature": 25,
                    "timestamp": datetime.now().isoformat(),
                    "count": telemetry_count
                }
                
                telemetry_data = json.dumps(telemetry).encode('utf-8')
                
                # Send to relay
                telemetry_socket.sendto(
                    telemetry_data,
                    (self.relay_ip, self.telemetry_port)
                )
                
                print(f"[DRONE] Sent telemetry #{telemetry_count}")
                telemetry_count += 1
                
                time.sleep(2)
                
            except Exception as e:
                print(f"[DRONE] Error: {e}")
                break
        
        command_socket.close()
        telemetry_socket.close()
        print("[DRONE] Drone simulator stopped")
    
    def monitor_relay(self):
        """Monitor relay communication"""
        print("Starting relay monitor...")
        
        # Monitor telemetry from relay
        telemetry_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        telemetry_socket.bind(("0.0.0.0", self.telemetry_port))
        telemetry_socket.settimeout(1.0)
        
        while self.running:
            try:
                data, addr = telemetry_socket.recvfrom(4096)
                
                try:
                    # Try to parse as JSON
                    telemetry = json.loads(data.decode('utf-8'))
                    print(f"[MONITOR] Telemetry from {addr}: {telemetry}")
                except json.JSONDecodeError:
                    # Raw data
                    print(f"[MONITOR] Raw data from {addr}: {data}")
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[MONITOR] Error: {e}")
        
        telemetry_socket.close()
        print("[MONITOR] Relay monitor stopped")
    
    def test_connectivity(self):
        """Test basic connectivity to relay"""
        print("Testing connectivity to relay...")
        
        # Test command port
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            test_socket.settimeout(2.0)
            
            # Send test command
            test_socket.sendto(b"test", (self.relay_ip, self.command_port))
            print(f"✓ Command port {self.command_port} accessible")
            test_socket.close()
            
        except Exception as e:
            print(f"✗ Command port {self.command_port} error: {e}")
        
        # Test if telemetry port is listening
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            test_socket.bind(("0.0.0.0", 9999))  # Use different port
            test_socket.settimeout(1.0)
            
            # Try to connect (UDP doesn't really connect, but this tests routing)
            test_socket.sendto(b"ping", (self.relay_ip, self.telemetry_port))
            print(f"✓ Can send to telemetry port {self.telemetry_port}")
            test_socket.close()
            
        except Exception as e:
            print(f"✗ Telemetry port {self.telemetry_port} error: {e}")
        
        print("Connectivity test complete")
    
    def start_test(self, mode):
        """Start the test in specified mode"""
        self.running = True
        
        if mode == "base":
            self.simulate_base_station()
        elif mode == "drone":
            self.simulate_drone()
        elif mode == "monitor":
            self.monitor_relay()
        elif mode == "full":
            # Start all simulators
            base_thread = threading.Thread(target=self.simulate_base_station)
            drone_thread = threading.Thread(target=self.simulate_drone)
            monitor_thread = threading.Thread(target=self.monitor_relay)
            
            base_thread.daemon = True
            drone_thread.daemon = True
            monitor_thread.daemon = True
            
            base_thread.start()
            drone_thread.start()
            monitor_thread.start()
            
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nShutting down...")
                self.running = False
        
        elif mode == "test":
            self.test_connectivity()
    
    def stop(self):
        """Stop the test"""
        self.running = False

def main():
    parser = argparse.ArgumentParser(description='Drone Relay Test Tool')
    parser.add_argument('mode', choices=['base', 'drone', 'monitor', 'full', 'test'],
                       help='Test mode to run')
    parser.add_argument('--relay-ip', default='10.0.0.4',
                       help='IP address of the relay (default: 10.0.0.4)')
    parser.add_argument('--base-ip', default='10.0.0.3',
                       help='IP address of the base station (default: 10.0.0.3)')
    parser.add_argument('--drone-ip', default='10.0.0.5',
                       help='IP address of the drone (default: 10.0.0.5)')
    
    args = parser.parse_args()
    
    tester = RelayTester()
    tester.relay_ip = args.relay_ip
    tester.base_station_ip = args.base_ip
    tester.drone_ip = args.drone_ip
    
    print(f"Starting relay test in '{args.mode}' mode")
    print(f"Relay IP: {tester.relay_ip}")
    print(f"Base Station IP: {tester.base_station_ip}")
    print(f"Drone IP: {tester.drone_ip}")
    print()
    
    try:
        tester.start_test(args.mode)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    finally:
        tester.stop()

if __name__ == '__main__':
    main()
