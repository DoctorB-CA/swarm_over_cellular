#!/usr/bin/env python3
"""
Raspberry Pi Drone Communication Relay with RTP Video
"""

import socket
import threading
import time
import logging
import signal
import sys
import subprocess
from typing import Optional
from datetime import datetime

# Import configuration
from relay_config import *

class DroneRelayRTP:
    """Main relay class with FFmpeg RTP video forwarding"""
    
    def __init__(self):
        self.running = False
        self.threads = []
        self.sockets = {}
        self.ffmpeg_process = None
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, LOG_LEVEL),
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Statistics
        self.statistics = {
            'commands_forwarded': 0,
            'telemetry_forwarded': 0,
            'video_bytes_forwarded': 0,
            'errors': 0,
            'start_time': datetime.now()
        }

    def start(self):
        """Start the relay service"""
        self.logger.info("Starting Drone Relay with RTP video...")
        self.logger.info(f"Base Station: {BASE_STATION_IP}")
        self.logger.info(f"Drone: {DRONE_IP}")
        
        try:
            self.running = True
            
            # Start command relay
            if ENABLE_COMMAND_RELAY:
                self.start_command_relay()
            
            # Start telemetry relay  
            if ENABLE_TELEMETRY_RELAY:
                self.start_telemetry_relay()
            
            # Start FFmpeg RTP video relay
            if ENABLE_VIDEO_RELAY:
                self.start_rtp_video_relay()
            
            self.logger.info("All relay services started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start relay: {e}")
            self.stop()
            return False

    def start_command_relay(self):
        """Start command relay: Base Station -> Drone"""
        def command_worker():
            try:
                cmd_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                cmd_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                cmd_socket.bind((BIND_COMMAND_INTERFACE, BASE_STATION_COMMAND_PORT))
                cmd_socket.settimeout(SOCKET_TIMEOUT)
                
                drone_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                
                self.sockets['command_rx'] = cmd_socket
                self.sockets['command_tx'] = drone_socket
                
                self.logger.info(f"Command relay: {BASE_STATION_COMMAND_PORT} -> {DRONE_IP}:{DRONE_COMMAND_PORT}")
                
                while self.running:
                    try:
                        data, addr = cmd_socket.recvfrom(BUFFER_SIZE)
                        drone_socket.sendto(data, (DRONE_IP, DRONE_COMMAND_PORT))
                        self.statistics['commands_forwarded'] += 1
                        
                        if ENABLE_PACKET_LOGGING:
                            self.logger.debug(f"Command forwarded: {data.decode('utf-8', errors='ignore')}")
                            
                    except socket.timeout:
                        continue
                    except Exception as e:
                        if self.running:
                            self.logger.error(f"Command relay error: {e}")
                            self.statistics['errors'] += 1
                            
            except Exception as e:
                self.logger.error(f"Command relay setup error: {e}")
        
        thread = threading.Thread(target=command_worker, name="CommandRelay")
        thread.daemon = True
        thread.start()
        self.threads.append(thread)

    def start_telemetry_relay(self):
        """Start telemetry relay: Drone -> Base Station"""
        def telemetry_worker():
            try:
                tel_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                tel_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                tel_socket.bind((BIND_TELEMETRY_INTERFACE, DRONE_TELEMETRY_PORT))
                tel_socket.settimeout(SOCKET_TIMEOUT)
                
                base_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                
                self.sockets['telemetry_rx'] = tel_socket
                self.sockets['telemetry_tx'] = base_socket
                
                self.logger.info(f"Telemetry relay: {DRONE_TELEMETRY_PORT} -> {BASE_STATION_IP}:{BASE_STATION_TELEMETRY_PORT}")
                
                while self.running:
                    try:
                        data, addr = tel_socket.recvfrom(BUFFER_SIZE)
                        base_socket.sendto(data, (BASE_STATION_IP, BASE_STATION_TELEMETRY_PORT))
                        self.statistics['telemetry_forwarded'] += 1
                        
                        if ENABLE_PACKET_LOGGING:
                            self.logger.debug(f"Telemetry forwarded: {len(data)} bytes")
                            
                    except socket.timeout:
                        continue
                    except Exception as e:
                        if self.running:
                            self.logger.error(f"Telemetry relay error: {e}")
                            self.statistics['errors'] += 1
                            
            except Exception as e:
                self.logger.error(f"Telemetry relay setup error: {e}")
        
        thread = threading.Thread(target=telemetry_worker, name="TelemetryRelay")
        thread.daemon = True
        thread.start()
        self.threads.append(thread)

    def start_rtp_video_relay(self):
        """Start FFmpeg RTP video relay: Drone -> Base Station"""
        def video_worker():
            try:
                # FFmpeg command to receive raw drone video and convert to RTP
                ffmpeg_cmd = [
                    'ffmpeg',
                    '-f', 'h264',  # Input format from drone
                    '-i', f'udp://0.0.0.0:{DRONE_VIDEO_PORT}?fifo_size=1000000&overrun_nonfatal=1',
                    '-c', 'copy',  # Copy stream without re-encoding
                    '-f', 'rtp',   # Output as RTP
                    f'rtp://{BASE_STATION_IP}:{BASE_STATION_VIDEO_PORT}?pkt_size={RTP_PACKET_SIZE}'
                ]
                
                self.logger.info(f"Starting FFmpeg RTP video relay: {DRONE_VIDEO_PORT} -> {BASE_STATION_IP}:{BASE_STATION_VIDEO_PORT}")
                self.logger.info(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
                
                self.ffmpeg_process = subprocess.Popen(
                    ffmpeg_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=0
                )
                
                # Monitor FFmpeg process
                while self.running:
                    if self.ffmpeg_process.poll() is not None:
                        stdout, stderr = self.ffmpeg_process.communicate()
                        self.logger.error(f"FFmpeg process ended unexpectedly")
                        if stderr:
                            self.logger.error(f"FFmpeg stderr: {stderr.decode('utf-8')}")
                        
                        if self.running:
                            self.logger.info("Attempting to restart FFmpeg...")
                            time.sleep(2)
                            self.ffmpeg_process = subprocess.Popen(
                                ffmpeg_cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                bufsize=0
                            )
                        break
                    
                    time.sleep(1)
                    
            except Exception as e:
                self.logger.error(f"Video relay error: {e}")
        
        thread = threading.Thread(target=video_worker, name="VideoRelay")
        thread.daemon = True
        thread.start()
        self.threads.append(thread)

    def stop(self):
        """Stop the relay service"""
        self.logger.info("Stopping relay service...")
        self.running = False
        
        # Stop FFmpeg process
        if self.ffmpeg_process:
            try:
                self.ffmpeg_process.terminate()
                self.ffmpeg_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.ffmpeg_process.kill()
            except Exception as e:
                self.logger.error(f"Error stopping FFmpeg: {e}")
        
        # Close sockets
        for socket_obj in self.sockets.values():
            try:
                socket_obj.close()
            except:
                pass
        
        self.logger.info("Relay service stopped")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print("\nShutdown signal received...")
    if 'relay' in globals():
        relay.stop()
    sys.exit(0)

if __name__ == '__main__':
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start relay
    relay = DroneRelayRTP()
    
    if relay.start():
        try:
            while True:
                time.sleep(5)
                # Print statistics every 30 seconds
                if int(time.time()) % 30 == 0:
                    uptime = datetime.now() - relay.statistics['start_time']
                    relay.logger.info(f"Stats - Commands: {relay.statistics['commands_forwarded']}, "
                                    f"Telemetry: {relay.statistics['telemetry_forwarded']}, "
                                    f"Errors: {relay.statistics['errors']}, "
                                    f"Uptime: {uptime}")
        except KeyboardInterrupt:
            pass
    
    relay.stop()