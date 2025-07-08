#!/usr/bin/env python3
"""
Communication Bridge for Raspberry Pi
Acts as a relay between the drone and the control station over cellular network.
This script runs on the Raspberry Pi and forwards communication bidirectionally.
"""

import socket
import threading
import time
import json
import argparse
import signal
import sys
import logging
from datetime import datetime

# Import network configuration
try:
    from bridge_config import (
        DRONE_LOCAL_IP as DRONE_IP, 
        CONTROL_STATION_PUBLIC_IP as CONTROL_STATION_IP,
        BRIDGE_COMMAND_PORT as COMMAND_PORT,
        BRIDGE_TELEMETRY_PORT as TELEMETRY_PORT,
        BRIDGE_VIDEO_PORT as VIDEO_PORT,
        BRIDGE_RTP_PORT as RTP_VIDEO_PORT,
        BUFFER_SIZE as MAX_PACKET_SIZE,
        SOCKET_TIMEOUT,
        # Import original ports for forwarding
        CONTROL_COMMAND_PORT,
        CONTROL_TELEMETRY_PORT,
        CONTROL_VIDEO_PORT,
        CONTROL_RTP_PORT
    )
    # Original drone ports (where drone expects to receive)
    DRONE_COMMAND_PORT = 8889
    DRONE_TELEMETRY_PORT = 8888
    DRONE_VIDEO_PORT = 8890
    DRONE_RTP_PORT = 5000
except ImportError:
    # Fallback to base station config if bridge_config not available
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from base_station.connection.network_config import (
        DRONE_IP, CONTROL_STATION_IP, COMMAND_PORT, TELEMETRY_PORT, 
        VIDEO_PORT, RTP_VIDEO_PORT, SOCKET_TIMEOUT, MAX_PACKET_SIZE
    )
    # Use same ports for forwarding in fallback mode
    DRONE_COMMAND_PORT = COMMAND_PORT
    DRONE_TELEMETRY_PORT = TELEMETRY_PORT
    DRONE_VIDEO_PORT = VIDEO_PORT
    DRONE_RTP_PORT = RTP_VIDEO_PORT
    CONTROL_COMMAND_PORT = COMMAND_PORT
    CONTROL_TELEMETRY_PORT = TELEMETRY_PORT
    CONTROL_VIDEO_PORT = VIDEO_PORT
    CONTROL_RTP_PORT = RTP_VIDEO_PORT

# Add missing SOCKET_TIMEOUT if not in bridge_config
try:
    SOCKET_TIMEOUT
except NameError:
    SOCKET_TIMEOUT = 1.0

class CommunicationBridge:
    """Bridge for relaying communication between drone and control station"""
    
    def __init__(self, drone_ip=DRONE_IP, control_station_ip=CONTROL_STATION_IP,
                 command_port=COMMAND_PORT, telemetry_port=TELEMETRY_PORT,
                 video_port=VIDEO_PORT, rtp_video_port=RTP_VIDEO_PORT, 
                 verbose=False):
        """Initialize the communication bridge"""
        self.drone_ip = drone_ip
        self.control_station_ip = control_station_ip
        self.command_port = command_port
        self.telemetry_port = telemetry_port
        self.video_port = video_port
        self.rtp_video_port = rtp_video_port
        self.verbose = verbose
        
        # Socket objects
        self.command_from_control = None    # Receives commands from control station
        self.command_to_drone = None        # Sends commands to drone
        self.telemetry_from_drone = None    # Receives telemetry from drone
        self.telemetry_to_control = None    # Sends telemetry to control station
        self.video_from_drone = None        # Receives video from drone
        self.video_to_control = None        # Sends video to control station
        self.rtp_from_drone = None          # Receives RTP video from drone
        self.rtp_to_control = None          # Sends RTP video to control station
        
        # Thread management
        self.running = False
        self.threads = []
        
        # Statistics
        self.stats = {
            'commands_relayed': 0,
            'telemetry_relayed': 0,
            'video_packets_relayed': 0,
            'rtp_packets_relayed': 0,
            'start_time': None,
            'last_command_time': None,
            'last_telemetry_time': None,
            'last_video_time': None
        }
        
        # Setup logging
        self.setup_logging()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.handle_interrupt)
        signal.signal(signal.SIGTERM, self.handle_interrupt)
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('/tmp/communication_bridge.log')
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def handle_interrupt(self, signum, frame):
        """Handle interrupt signals for graceful shutdown"""
        self.logger.info("Interrupt received, shutting down bridge...")
        self.stop()
        sys.exit(0)
    
    def create_sockets(self):
        """Create and configure all required sockets"""
        try:
            # Enable socket reuse to avoid "address already in use" errors
            socket_options = socket.SO_REUSEADDR
            
            # Command relay sockets
            # Listen for commands from control station
            self.command_from_control = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.command_from_control.setsockopt(socket.SOL_SOCKET, socket_options, 1)
            self.command_from_control.bind(('0.0.0.0', self.command_port))
            self.command_from_control.settimeout(SOCKET_TIMEOUT)
            
            # Send commands to drone
            self.command_to_drone = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Telemetry relay sockets
            # Listen for telemetry from drone
            self.telemetry_from_drone = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.telemetry_from_drone.setsockopt(socket.SOL_SOCKET, socket_options, 1)
            self.telemetry_from_drone.bind(('0.0.0.0', self.telemetry_port))
            self.telemetry_from_drone.settimeout(SOCKET_TIMEOUT)
            
            # Send telemetry to control station
            self.telemetry_to_control = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Video relay sockets (legacy)
            # Listen for video from drone
            self.video_from_drone = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.video_from_drone.setsockopt(socket.SOL_SOCKET, socket_options, 1)
            self.video_from_drone.bind(('0.0.0.0', self.video_port))
            self.video_from_drone.settimeout(SOCKET_TIMEOUT)
            
            # Send video to control station
            self.video_to_control = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # RTP video relay sockets
            # Listen for RTP video from drone
            self.rtp_from_drone = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.rtp_from_drone.setsockopt(socket.SOL_SOCKET, socket_options, 1)
            self.rtp_from_drone.bind(('0.0.0.0', self.rtp_video_port))
            self.rtp_from_drone.settimeout(SOCKET_TIMEOUT)
            
            # Send RTP video to control station
            self.rtp_to_control = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            self.logger.info("All sockets created successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating sockets: {e}")
            return False
    
    def relay_commands(self):
        """Relay commands from control station to drone"""
        self.logger.info("Starting command relay thread")
        
        while self.running:
            try:
                # Receive command from control station
                data, addr = self.command_from_control.recvfrom(MAX_PACKET_SIZE)
                
                if data:
                    # Forward command to drone (use original drone port, not bridge port)
                    self.command_to_drone.sendto(data, (self.drone_ip, DRONE_COMMAND_PORT))
                    
                    # Update statistics
                    self.stats['commands_relayed'] += 1
                    self.stats['last_command_time'] = datetime.now()
                    
                    command_str = data.decode('utf-8', errors='ignore')
                    self.logger.debug(f"Relayed command: {command_str} from {addr}")
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error in command relay: {e}")
    
    def relay_telemetry(self):
        """Relay telemetry from drone to control station"""
        self.logger.info("Starting telemetry relay thread")
        
        while self.running:
            try:
                # Receive telemetry from drone
                data, addr = self.telemetry_from_drone.recvfrom(MAX_PACKET_SIZE)
                
                if data:
                    # Forward telemetry to control station (use original control station port)
                    self.telemetry_to_control.sendto(data, (self.control_station_ip, CONTROL_TELEMETRY_PORT))
                    
                    # Update statistics
                    self.stats['telemetry_relayed'] += 1
                    self.stats['last_telemetry_time'] = datetime.now()
                    
                    # Log telemetry if verbose
                    if self.verbose:
                        try:
                            telemetry = json.loads(data.decode('utf-8'))
                            self.logger.debug(f"Relayed telemetry: {telemetry}")
                        except:
                            self.logger.debug(f"Relayed telemetry: {len(data)} bytes")
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error in telemetry relay: {e}")
    
    def relay_video(self):
        """Relay legacy video from drone to control station"""
        self.logger.info("Starting legacy video relay thread")
        
        while self.running:
            try:
                # Receive video from drone
                data, addr = self.video_from_drone.recvfrom(MAX_PACKET_SIZE)
                
                if data:
                    # Forward video to control station
                    self.video_to_control.sendto(data, (self.control_station_ip, self.video_port))
                    
                    # Update statistics
                    self.stats['video_packets_relayed'] += 1
                    self.stats['last_video_time'] = datetime.now()
                    
                    self.logger.debug(f"Relayed video packet: {len(data)} bytes")
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error in video relay: {e}")
    
    def relay_rtp_video(self):
        """Relay RTP video from drone to control station"""
        self.logger.info("Starting RTP video relay thread")
        
        while self.running:
            try:
                # Receive RTP video from drone
                data, addr = self.rtp_from_drone.recvfrom(MAX_PACKET_SIZE)
                
                if data:
                    # Forward RTP video to control station
                    self.rtp_to_control.sendto(data, (self.control_station_ip, self.rtp_video_port))
                    
                    # Update statistics
                    self.stats['rtp_packets_relayed'] += 1
                    
                    self.logger.debug(f"Relayed RTP packet: {len(data)} bytes")
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error in RTP video relay: {e}")
    
    def print_statistics(self):
        """Print relay statistics periodically"""
        while self.running:
            time.sleep(30)  # Print stats every 30 seconds
            
            if self.stats['start_time']:
                uptime = datetime.now() - self.stats['start_time']
                self.logger.info(f"Bridge Statistics - Uptime: {uptime}")
                self.logger.info(f"Commands relayed: {self.stats['commands_relayed']}")
                self.logger.info(f"Telemetry packets relayed: {self.stats['telemetry_relayed']}")
                self.logger.info(f"Video packets relayed: {self.stats['video_packets_relayed']}")
                self.logger.info(f"RTP packets relayed: {self.stats['rtp_packets_relayed']}")
                
                if self.stats['last_command_time']:
                    self.logger.info(f"Last command: {self.stats['last_command_time'].strftime('%H:%M:%S')}")
                if self.stats['last_telemetry_time']:
                    self.logger.info(f"Last telemetry: {self.stats['last_telemetry_time'].strftime('%H:%M:%S')}")
    
    def start(self):
        """Start the communication bridge"""
        self.logger.info("Starting Communication Bridge")
        self.logger.info(f"Drone IP: {self.drone_ip}")
        self.logger.info(f"Control Station IP: {self.control_station_ip}")
        self.logger.info(f"Command Port: {self.command_port}")
        self.logger.info(f"Telemetry Port: {self.telemetry_port}")
        self.logger.info(f"Video Port: {self.video_port}")
        self.logger.info(f"RTP Video Port: {self.rtp_video_port}")
        
        # Create sockets
        if not self.create_sockets():
            self.logger.error("Failed to create sockets")
            return False
        
        # Start bridge
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        # Create and start threads
        threads_config = [
            ('command_relay', self.relay_commands),
            ('telemetry_relay', self.relay_telemetry),
            ('video_relay', self.relay_video),
            ('rtp_video_relay', self.relay_rtp_video),
            ('statistics', self.print_statistics)
        ]
        
        for thread_name, thread_func in threads_config:
            thread = threading.Thread(target=thread_func, name=thread_name)
            thread.daemon = True
            thread.start()
            self.threads.append(thread)
        
        self.logger.info("Communication bridge started successfully")
        self.logger.info("Press Ctrl+C to stop")
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.handle_interrupt(None, None)
        
        return True
    
    def stop(self):
        """Stop the communication bridge"""
        self.logger.info("Stopping communication bridge...")
        self.running = False
        
        # Wait for threads to finish
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=2.0)
        
        # Close all sockets
        sockets = [
            self.command_from_control, self.command_to_drone,
            self.telemetry_from_drone, self.telemetry_to_control,
            self.video_from_drone, self.video_to_control,
            self.rtp_from_drone, self.rtp_to_control
        ]
        
        for sock in sockets:
            if sock:
                try:
                    sock.close()
                except:
                    pass
        
        # Print final statistics
        if self.stats['start_time']:
            uptime = datetime.now() - self.stats['start_time']
            self.logger.info(f"Final Statistics - Total uptime: {uptime}")
            self.logger.info(f"Total commands relayed: {self.stats['commands_relayed']}")
            self.logger.info(f"Total telemetry packets relayed: {self.stats['telemetry_relayed']}")
            self.logger.info(f"Total video packets relayed: {self.stats['video_packets_relayed']}")
            self.logger.info(f"Total RTP packets relayed: {self.stats['rtp_packets_relayed']}")
        
        self.logger.info("Communication bridge stopped")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Communication Bridge for Drone Control')
    parser.add_argument('--drone-ip', default=DRONE_IP, 
                       help=f'IP address of the drone (default: {DRONE_IP})')
    parser.add_argument('--control-ip', default=CONTROL_STATION_IP,
                       help=f'IP address of the control station (default: {CONTROL_STATION_IP})')
    parser.add_argument('--command-port', type=int, default=COMMAND_PORT,
                       help=f'Command port (default: {COMMAND_PORT})')
    parser.add_argument('--telemetry-port', type=int, default=TELEMETRY_PORT,
                       help=f'Telemetry port (default: {TELEMETRY_PORT})')
    parser.add_argument('--video-port', type=int, default=VIDEO_PORT,
                       help=f'Video port (default: {VIDEO_PORT})')
    parser.add_argument('--rtp-port', type=int, default=RTP_VIDEO_PORT,
                       help=f'RTP video port (default: {RTP_VIDEO_PORT})')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Create and start bridge
    bridge = CommunicationBridge(
        drone_ip=args.drone_ip,
        control_station_ip=args.control_ip,
        command_port=args.command_port,
        telemetry_port=args.telemetry_port,
        video_port=args.video_port,
        rtp_video_port=args.rtp_port,
        verbose=args.verbose
    )
    
    bridge.start()


if __name__ == "__main__":
    main()
