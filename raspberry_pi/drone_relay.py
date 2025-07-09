#!/usr/bin/env python3
"""
Raspberry Pi Drone Communication Relay

This script acts as a relay between a base station and a drone, forwarding:
- Commands from base station to drone
- Telemetry from drone to base station
- Video stream from drone to base station

The relay runs on a Raspberry Pi and handles the communication bridge
between different network segments.
"""

import socket
import threading
import time
import logging
import signal
import sys
from typing import Optional, Tuple
import subprocess
import json
from datetime import datetime

# Import configuration
from relay_config import *

class DroneRelay:
    """Main relay class that handles all communication forwarding"""
    
    def __init__(self):
        self.running = False
        self.threads = []
        self.sockets = {}
        self.statistics = {
            'commands_forwarded': 0,
            'telemetry_forwarded': 0,
            'video_bytes_forwarded': 0,
            'start_time': None,
            'last_command_time': None,
            'last_telemetry_time': None,
            'errors': 0
        }
        
        # Setup logging
        self.setup_logging()
        
        # Video relay process
        self.video_process = None
        
        self.logger.info("Drone Relay initialized")
    
    def make_json_safe(self, obj):
        """Convert an object to be JSON serializable"""
        if obj is None:
            return None
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: self.make_json_safe(value) for key, value in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self.make_json_safe(item) for item in obj]
        else:
            return obj
    
    def setup_logging(self):
        """Setup logging configuration"""
        import os
        
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # Try primary log file first, then fallback
        log_file = LOG_FILE
        try:
            # Test if we can write to the primary log file
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            with open(log_file, 'a') as f:
                pass  # Just test if we can open for writing
        except (PermissionError, OSError):
            # Use fallback location
            try:
                log_file = os.path.expanduser(LOG_FILE_FALLBACK)
            except NameError:
                # If LOG_FILE_FALLBACK is not defined
                log_file = os.path.expanduser("~/drone_relay.log")
            print(f"Warning: Cannot write to {LOG_FILE}, using fallback: {log_file}")
        
        # Configure root logger
        logging.basicConfig(
            level=getattr(logging, LOG_LEVEL),
            format=log_format,
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger('DroneRelay')
    
    def create_socket(self, name: str, bind_ip: str, bind_port: int) -> socket.socket:
        """Create and configure a UDP socket"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(SOCKET_TIMEOUT)
            sock.bind((bind_ip, bind_port))
            
            self.sockets[name] = sock
            self.logger.info(f"Created socket {name} bound to {bind_ip}:{bind_port}")
            return sock
            
        except Exception as e:
            self.logger.error(f"Failed to create socket {name}: {e}")
            raise
    
    def start(self):
        """Start the relay system"""
        self.logger.info("Starting Drone Relay System")
        self.running = True
        self.statistics['start_time'] = datetime.now()
        
        try:
            # Start command relay
            if ENABLE_COMMAND_RELAY:
                self.start_command_relay()
            
            # Start telemetry relay
            if ENABLE_TELEMETRY_RELAY:
                self.start_telemetry_relay()
            
            # Start video relay
            if ENABLE_VIDEO_RELAY:
                self.start_video_relay()
            
            # Start heartbeat
            if ENABLE_HEARTBEAT:
                self.start_heartbeat()
            
            # Start statistics reporting
            if ENABLE_STATISTICS:
                self.start_statistics_reporter()
            
            self.logger.info("All relay services started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start relay: {e}")
            self.stop()
            raise
    
    def start_command_relay(self):
        """Start the command relay thread"""
        def command_relay_worker():
            self.logger.info("Starting command relay worker")
            
            # Create socket to receive commands from base station
            command_socket = self.create_socket(
                'command_rx', 
                BIND_COMMAND_INTERFACE, 
                BASE_STATION_COMMAND_PORT
            )
            
            # Create socket to send commands to drone
            drone_command_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sockets['command_tx'] = drone_command_socket
            
            while self.running:
                try:
                    # Receive command from base station
                    data, addr = command_socket.recvfrom(BUFFER_SIZE)
                    
                    # Verify sender is authorized
                    if addr[0] not in ALLOWED_BASE_STATIONS:
                        self.logger.warning(f"Unauthorized command from {addr[0]}")
                        continue
                    
                    # Log command if enabled
                    if ENABLE_PACKET_LOGGING:
                        self.logger.debug(f"Command received from {addr}: {data}")
                    
                    # Forward command to drone
                    drone_command_socket.sendto(data, (DRONE_IP, DRONE_COMMAND_PORT))
                    
                    # Update statistics
                    self.statistics['commands_forwarded'] += 1
                    self.statistics['last_command_time'] = datetime.now()
                    
                    self.logger.debug(f"Forwarded command: {data.decode('utf-8', errors='ignore')}")
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        self.logger.error(f"Command relay error: {e}")
                        self.statistics['errors'] += 1
        
        thread = threading.Thread(target=command_relay_worker, name="CommandRelay")
        thread.daemon = True
        thread.start()
        self.threads.append(thread)
    
    def start_telemetry_relay(self):
        """Start the telemetry relay thread"""
        def telemetry_relay_worker():
            self.logger.info("Starting telemetry relay worker")
            
            # Create socket to receive telemetry from drone
            telemetry_socket = self.create_socket(
                'telemetry_rx',
                BIND_TELEMETRY_INTERFACE,
                DRONE_TELEMETRY_PORT
            )
            
            # Create socket to send telemetry to base station
            base_telemetry_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sockets['telemetry_tx'] = base_telemetry_socket
            
            while self.running:
                try:
                    # Receive telemetry from drone
                    data, addr = telemetry_socket.recvfrom(BUFFER_SIZE)
                    
                    # Log telemetry if enabled
                    if ENABLE_PACKET_LOGGING:
                        self.logger.debug(f"Telemetry received from {addr}: {data}")
                    
                    # Forward telemetry to base station
                    base_telemetry_socket.sendto(
                        data, 
                        (BASE_STATION_IP, BASE_STATION_TELEMETRY_PORT)
                    )
                    
                    # Update statistics
                    self.statistics['telemetry_forwarded'] += 1
                    self.statistics['last_telemetry_time'] = datetime.now()
                    
                    self.logger.debug(f"Forwarded telemetry data ({len(data)} bytes)")
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        self.logger.error(f"Telemetry relay error: {e}")
                        self.statistics['errors'] += 1
        
        thread = threading.Thread(target=telemetry_relay_worker, name="TelemetryRelay")
        thread.daemon = True
        thread.start()
        self.threads.append(thread)
    
    def start_video_relay(self):
        """Start the video relay using FFmpeg"""
        def video_relay_worker():
            self.logger.info("Starting video relay worker")
            
            try:
                # FFmpeg command to relay video from drone to base station
                # Receives from drone's video port and forwards as RTP to base station
                ffmpeg_cmd = [
                    'ffmpeg',
                    '-f', 'h264',
                    '-i', f'udp://0.0.0.0:{DRONE_VIDEO_PORT}',
                    '-c', 'copy',  # Copy without re-encoding
                    '-f', 'rtp',
                    f'rtp://{BASE_STATION_IP}:{BASE_STATION_VIDEO_PORT}'
                ]
                
                self.logger.info(f"Starting FFmpeg video relay: {' '.join(ffmpeg_cmd)}")
                
                # Start FFmpeg process
                self.video_process = subprocess.Popen(
                    ffmpeg_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                
                # Monitor FFmpeg process
                while self.running:
                    if self.video_process.poll() is not None:
                        # Process terminated
                        stdout, stderr = self.video_process.communicate()
                        self.logger.error(f"FFmpeg terminated. Stdout: {stdout}, Stderr: {stderr}")
                        
                        if self.running:
                            # Try to restart
                            self.logger.info("Attempting to restart video relay...")
                            time.sleep(2)
                            self.video_process = subprocess.Popen(ffmpeg_cmd, 
                                                                stdout=subprocess.PIPE, 
                                                                stderr=subprocess.PIPE)
                    
                    time.sleep(1)
                    
            except Exception as e:
                self.logger.error(f"Video relay error: {e}")
                self.statistics['errors'] += 1
        
        thread = threading.Thread(target=video_relay_worker, name="VideoRelay")
        thread.daemon = True
        thread.start()
        self.threads.append(thread)
    
    def start_heartbeat(self):
        """Start heartbeat/keepalive functionality"""
        def heartbeat_worker():
            self.logger.info("Starting heartbeat worker")
            
            heartbeat_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sockets['heartbeat'] = heartbeat_socket
            
            while self.running:
                try:
                    # Create JSON-serializable statistics using the safe method
                    stats_copy = self.make_json_safe(self.statistics)
                    
                    # Send heartbeat to base station
                    heartbeat_data = json.dumps({
                        'type': 'heartbeat',
                        'timestamp': datetime.now().isoformat(),
                        'relay_status': 'active',
                        'statistics': stats_copy
                    }).encode('utf-8')
                    
                    heartbeat_socket.sendto(
                        heartbeat_data,
                        (BASE_STATION_IP, BASE_STATION_TELEMETRY_PORT)
                    )
                    
                    time.sleep(KEEPALIVE_INTERVAL)
                    
                except Exception as e:
                    if self.running:
                        self.logger.error(f"Heartbeat error: {e}")
                        # Add more debugging info
                        import traceback
                        self.logger.debug(f"Heartbeat traceback: {traceback.format_exc()}")
        
        thread = threading.Thread(target=heartbeat_worker, name="Heartbeat")
        thread.daemon = True
        thread.start()
        self.threads.append(thread)
    
    def start_statistics_reporter(self):
        """Start statistics reporting thread"""
        def statistics_worker():
            while self.running:
                time.sleep(30)  # Report every 30 seconds
                if self.running:
                    self.log_statistics()
        
        thread = threading.Thread(target=statistics_worker, name="Statistics")
        thread.daemon = True
        thread.start()
        self.threads.append(thread)
    
    def log_statistics(self):
        """Log current statistics"""
        if self.statistics['start_time']:
            uptime = datetime.now() - self.statistics['start_time']
            self.logger.info(f"Relay Statistics - Uptime: {uptime}, "
                           f"Commands: {self.statistics['commands_forwarded']}, "
                           f"Telemetry: {self.statistics['telemetry_forwarded']}, "
                           f"Video: {self.statistics['video_bytes_forwarded']} bytes, "
                           f"Errors: {self.statistics['errors']}")
    
    def stop(self):
        """Stop the relay system"""
        self.logger.info("Stopping Drone Relay System")
        self.running = False
        
        # Stop video process
        if self.video_process:
            try:
                self.video_process.terminate()
                self.video_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.video_process.kill()
            except Exception as e:
                self.logger.error(f"Error stopping video process: {e}")
        
        # Close all sockets
        for name, sock in self.sockets.items():
            try:
                sock.close()
                self.logger.debug(f"Closed socket {name}")
            except Exception as e:
                self.logger.error(f"Error closing socket {name}: {e}")
        
        # Wait for threads to finish
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=2)
        
        # Final statistics
        self.log_statistics()
        self.logger.info("Drone Relay System stopped")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"\nReceived signal {signum}, shutting down...")
    if 'relay' in globals():
        relay.stop()
    sys.exit(0)

def main():
    """Main function"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start relay
    global relay
    relay = DroneRelay()
    
    try:
        relay.start()
        
        # Keep main thread alive
        while relay.running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received")
    except Exception as e:
        relay.logger.error(f"Unexpected error: {e}")
    finally:
        relay.stop()

if __name__ == '__main__':
    main()
