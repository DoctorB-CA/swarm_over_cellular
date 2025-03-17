#!/usr/bin/env python3
import socket
import threading
import time
import random
import json
import argparse
import signal
import sys
import numpy as np
import base64
import cv2
from io import BytesIO
from PIL import Image

# Default network settings
DEFAULT_LISTEN_PORT = 8889      # Port to listen for commands from control station
DEFAULT_CONTROL_IP = "10.0.0.20"  # IP address of control station to send telemetry to
DEFAULT_CONTROL_PORT = 8888     # Port on control station to send telemetry to
DEFAULT_VIDEO_PORT = 8890       # Port for sending video frames

# Video settings
VIDEO_WIDTH = 640               # Width of the video frame
VIDEO_HEIGHT = 480              # Height of the video frame
VIDEO_FPS = 15                  # Frames per second for video stream
VIDEO_QUALITY = 70              # JPEG quality (0-100)
MAX_VIDEO_PACKET_SIZE = 65000   # Maximum UDP packet size for video

class HeadlessDroneSimulatorWithVideo:
    """Drone simulator that runs without GUI, sending telemetry and video data"""
    
    def __init__(self, listen_port=DEFAULT_LISTEN_PORT, control_ip=DEFAULT_CONTROL_IP, 
                control_port=DEFAULT_CONTROL_PORT, video_port=DEFAULT_VIDEO_PORT, 
                verbose=False):
        """Initialize the simulator"""
        self.listen_port = listen_port
        self.control_ip = control_ip
        self.control_port = control_port
        self.video_port = video_port
        self.verbose = verbose
        
        # Drone state
        self.is_flying = False
        self.battery = 100.0
        self.altitude = 0
        self.speed = 0
        self.x_position = 0
        self.y_position = 0
        self.rotation = 0        # Rotation in degrees
        self.frame_count = 0
        
        # Create UDP socket for receiving commands
        self.command_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.command_socket.bind(('0.0.0.0', self.listen_port))
        
        # Create UDP socket for sending telemetry
        self.telemetry_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Create UDP socket for sending video
        self.video_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Start threads
        self.running = True
        self.command_thread = threading.Thread(target=self.command_listener)
        self.telemetry_thread = threading.Thread(target=self.telemetry_sender)
        self.battery_thread = threading.Thread(target=self.battery_simulator)
        self.video_thread = threading.Thread(target=self.video_sender)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.handle_interrupt)
        signal.signal(signal.SIGTERM, self.handle_interrupt)
    
    def handle_interrupt(self, signum, frame):
        """Handle interrupt signals for graceful shutdown"""
        print("\nShutting down simulator...")
        self.stop()
        sys.exit(0)
        
    def log(self, message):
        """Log message if verbose mode is enabled"""
        if self.verbose:
            print(f"[{time.strftime('%H:%M:%S')}] {message}")
    
    def start(self):
        """Start the simulator threads"""
        self.command_thread.start()
        self.telemetry_thread.start()
        self.battery_thread.start()
        self.video_thread.start()
        print(f"Drone simulator listening for commands on port {self.listen_port}")
        print(f"Sending telemetry to {self.control_ip}:{self.control_port}")
        print(f"Sending video to {self.control_ip}:{self.video_port}")
        print("Press Ctrl+C to exit")
    
    def stop(self):
        """Stop the simulator"""
        self.running = False
        if self.command_thread.is_alive():
            self.command_thread.join(timeout=1.0)
        if self.telemetry_thread.is_alive():
            self.telemetry_thread.join(timeout=1.0)
        if self.battery_thread.is_alive():
            self.battery_thread.join(timeout=1.0)
        if self.video_thread.is_alive():
            self.video_thread.join(timeout=1.0)
        
        self.command_socket.close()
        self.telemetry_socket.close()
        self.video_socket.close()
        print("Simulator stopped")
    
    def command_listener(self):
        """Listen for incoming commands"""
        self.command_socket.settimeout(1.0)  # 1 second timeout for clean shutdown
        
        while self.running:
            try:
                data, addr = self.command_socket.recvfrom(1024)
                command = data.decode('utf-8')
                timestamp = time.strftime("%H:%M:%S", time.localtime())
                
                print(f"[{timestamp}] Received: {command} from {addr[0]}:{addr[1]}")
                
                # Process the command
                self.process_command(command)
                
                # Echo back a response (like a real drone would)
                response = "ok"
                self.command_socket.sendto(response.encode('utf-8'), addr)
                
            except socket.timeout:
                # This is just to allow for clean shutdown
                pass
            except Exception as e:
                print(f"Error receiving command: {e}")
    
    def process_command(self, command):
        """Process received commands and update drone state"""
        self.log(f"Processing command: {command}")
        
        if command == "command":
            # SDK mode activation - no state change
            self.log("Entered SDK mode")
        
        elif command == "takeoff":
            self.is_flying = True
            self.altitude = 100  # cm
            self.speed = 0
            print("TAKEOFF - Drone is now flying at 100cm altitude")
        
        elif command == "land":
            self.is_flying = False
            self.altitude = 0
            self.speed = 0
            self.x_position = 0
            self.y_position = 0
            print("LANDING - Drone has landed")
        
        elif command.startswith("forward"):
            if self.is_flying:
                try:
                    parts = command.split()
                    distance = int(parts[1]) if len(parts) > 1 else 20
                    self.y_position += distance
                    self.speed = 20  # Simulate speed change
                    print(f"Moving FORWARD {distance}cm (position: {self.x_position}, {self.y_position})")
                except:
                    print("Invalid forward command")
        
        elif command.startswith("backward"):
            if self.is_flying:
                try:
                    parts = command.split()
                    distance = int(parts[1]) if len(parts) > 1 else 20
                    self.y_position -= distance
                    self.speed = 20
                    print(f"Moving BACKWARD {distance}cm (position: {self.x_position}, {self.y_position})")
                except:
                    print("Invalid backward command")
        
        elif command.startswith("left"):
            if self.is_flying:
                try:
                    parts = command.split()
                    distance = int(parts[1]) if len(parts) > 1 else 20
                    self.x_position -= distance
                    self.speed = 15
                    print(f"Moving LEFT {distance}cm (position: {self.x_position}, {self.y_position})")
                except:
                    print("Invalid left command")
        
        elif command.startswith("right"):
            if self.is_flying:
                try:
                    parts = command.split()
                    distance = int(parts[1]) if len(parts) > 1 else 20
                    self.x_position += distance
                    self.speed = 15
                    print(f"Moving RIGHT {distance}cm (position: {self.x_position}, {self.y_position})")
                except:
                    print("Invalid right command")
                    
        elif command.startswith("cw"):
            if self.is_flying:
                try:
                    parts = command.split()
                    angle = int(parts[1]) if len(parts) > 1 else 45
                    self.rotation = (self.rotation + angle) % 360
                    print(f"Rotating CW by {angle} degrees (now at {self.rotation}°)")
                except:
                    print("Invalid cw command")
                    
        elif command.startswith("ccw"):
            if self.is_flying:
                try:
                    parts = command.split()
                    angle = int(parts[1]) if len(parts) > 1 else 45
                    self.rotation = (self.rotation - angle) % 360
                    print(f"Rotating CCW by {angle} degrees (now at {self.rotation}°)")
                except:
                    print("Invalid ccw command")
        
        else:
            print(f"Unknown command: {command}")
    
    def telemetry_sender(self):
        """Send telemetry data to the control station"""
        while self.running:
            # Create telemetry data
            telemetry = {
                "battery": self.battery,
                "altitude": self.altitude,
                "speed": self.speed,
                "x_position": self.x_position,
                "y_position": self.y_position,
                "rotation": self.rotation,
                "is_flying": self.is_flying,
                "timestamp": time.time()
            }
            
            # Send telemetry
            try:
                data = json.dumps(telemetry).encode('utf-8')
                self.telemetry_socket.sendto(data, (self.control_ip, self.control_port))
                self.log(f"Sent telemetry: {telemetry}")
            except Exception as e:
                print(f"Error sending telemetry: {e}")
            
            # Sleep for a short time
            time.sleep(0.2)  # Send telemetry more frequently (5 times per second)
    
    def battery_simulator(self):
        """Simulate battery drain"""
        while self.running:
            if self.is_flying:
                # Drain battery faster when flying
                self.battery = max(0, self.battery - 0.2)
                if self.battery < 20 and self.battery % 5 < 0.2:
                    print(f"WARNING: Battery low ({self.battery:.1f}%)")
                elif self.battery < 5:
                    print(f"CRITICAL: Battery critical ({self.battery:.1f}%)")
            else:
                # Slow drain when idle
                self.battery = max(0, self.battery - 0.05)
                
            # Add some random fluctuation to speed
            if self.is_flying:
                self.speed = max(0, self.speed + random.uniform(-2, 2))
                
            time.sleep(1)
            
    def generate_video_frame(self):
        """Generate a simulated video frame based on drone state"""
        # Create a blank frame
        frame = np.zeros((VIDEO_HEIGHT, VIDEO_WIDTH, 3), dtype=np.uint8)
        
        # Sky gradient (top half)
        for y in range(VIDEO_HEIGHT // 2):
            # Create sky gradient from blue to light blue
            blue = min(255, 150 + (y * 0.5))
            green = min(255, 150 + (y * 0.3))
            red = min(255, 100 + (y * 0.1))
            
            # Adjust based on altitude (higher = more blue)
            blue = min(255, blue + (self.altitude / 10))
            
            frame[y, :] = [blue, green, red]
        
        # Ground (bottom half)
        ground_start = VIDEO_HEIGHT // 2
        for y in range(ground_start, VIDEO_HEIGHT):
            # Create ground gradient
            rel_y = y - ground_start
            intensity = max(0, 190 - rel_y // 3)
            
            # Create a checkerboard pattern based on position
            pattern_size = 40
            for x in range(VIDEO_WIDTH):
                # Adjust pattern based on x,y position of drone
                offset_x = (x + self.x_position) % (pattern_size * 2)
                offset_y = (rel_y + self.y_position) % (pattern_size * 2)
                
                if ((offset_x // pattern_size) + (offset_y // pattern_size)) % 2 == 0:
                    frame[y, x] = [intensity - 20, intensity, intensity - 10]  # Lighter green
                else:
                    frame[y, x] = [intensity - 40, intensity - 20, intensity - 30]  # Darker green
        
        # Add a horizon line
        cv2.line(frame, (0, VIDEO_HEIGHT // 2), (VIDEO_WIDTH, VIDEO_HEIGHT // 2), (100, 100, 100), 1)
        
        # Add a drone direction indicator (a line pointing in the direction of travel)
        if self.is_flying:
            center_x, center_y = VIDEO_WIDTH // 2, 50
            radius = 20
            angle_rad = np.radians(self.rotation)
            end_x = int(center_x + radius * np.sin(angle_rad))
            end_y = int(center_y + radius * np.cos(angle_rad))
            
            # Draw the direction indicator
            cv2.circle(frame, (center_x, center_y), radius, (0, 0, 255), 2)
            cv2.line(frame, (center_x, center_y), (end_x, end_y), (0, 0, 255), 2)
        
        # Add text information
        text_color = (255, 255, 255)
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        
        # Add battery info
        battery_text = f"Battery: {self.battery:.1f}%"
        cv2.putText(frame, battery_text, (10, 30), font, font_scale, text_color, 1)
        
        # Add altitude info
        altitude_text = f"Alt: {self.altitude} cm"
        cv2.putText(frame, altitude_text, (10, 60), font, font_scale, text_color, 1)
        
        # Add speed info
        speed_text = f"Speed: {self.speed:.1f} cm/s"
        cv2.putText(frame, speed_text, (10, 90), font, font_scale, text_color, 1)
        
        # Add position info
        pos_text = f"Pos: ({self.x_position}, {self.y_position})"
        cv2.putText(frame, pos_text, (10, 120), font, font_scale, text_color, 1)
        
        # Add rotation info
        rot_text = f"Rot: {self.rotation}°"
        cv2.putText(frame, rot_text, (10, 150), font, font_scale, text_color, 1)
        
        # Add frame counter and timestamp
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        cv2.putText(frame, f"{timestamp} - Frame: {self.frame_count}", 
                   (VIDEO_WIDTH - 240, VIDEO_HEIGHT - 20), font, font_scale, text_color, 1)
        
        return frame
    
    def video_sender(self):
        """Generate and send simulated video frames"""
        frame_interval = 1.0 / VIDEO_FPS  # Time between frames
        
        while self.running:
            start_time = time.time()
            
            try:
                # Generate a frame
                frame = self.generate_video_frame()
                self.frame_count += 1
                
                # Compress the frame as JPEG
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, VIDEO_QUALITY])
                
                # Convert to bytes and send
                data = buffer.tobytes()
                
                # Add simple header with frame number and timestamp
                header = f"{self.frame_count}:{time.time()}".encode()
                
                # Prefix the data with the header length as a 2-byte value
                header_length = len(header)
                prefix = header_length.to_bytes(2, byteorder='big')
                
                # Combine prefix + header + image data
                packet = prefix + header + data
                
                # Send the frame
                if len(packet) > MAX_VIDEO_PACKET_SIZE:
                    print(f"Warning: Video packet size ({len(packet)} bytes) exceeds maximum ({MAX_VIDEO_PACKET_SIZE} bytes). Consider reducing quality.")
                
                self.video_socket.sendto(packet, (self.control_ip, self.video_port))
                self.log(f"Sent video frame {self.frame_count} ({len(data)} bytes)")
                
                # Calculate how long to sleep to maintain target FPS
                elapsed = time.time() - start_time
                sleep_time = max(0, frame_interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
            except Exception as e:
                print(f"Error sending video frame: {e}")
                time.sleep(frame_interval)  # Sleep and try again


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Headless Drone Simulator with Video')
    parser.add_argument('--listen-port', type=int, default=DEFAULT_LISTEN_PORT, 
                        help=f'Port to listen for commands (default: {DEFAULT_LISTEN_PORT})')
    parser.add_argument('--control-ip', type=str, default=DEFAULT_CONTROL_IP,
                        help=f'IP address to send telemetry and video to (default: {DEFAULT_CONTROL_IP})')
    parser.add_argument('--control-port', type=int, default=DEFAULT_CONTROL_PORT,
                        help=f'Port to send telemetry to (default: {DEFAULT_CONTROL_PORT})')
    parser.add_argument('--video-port', type=int, default=DEFAULT_VIDEO_PORT,
                        help=f'Port to send video to (default: {DEFAULT_VIDEO_PORT})')
    parser.add_argument('--video-quality', type=int, default=VIDEO_QUALITY,
                        help=f'JPEG quality for video (1-100, default: {VIDEO_QUALITY})')
    parser.add_argument('--video-fps', type=int, default=VIDEO_FPS,
                        help=f'Frames per second (default: {VIDEO_FPS})')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output')
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    
    # Update globals based on args
    VIDEO_QUALITY = args.video_quality
    VIDEO_FPS = args.video_fps
    
    print("Headless Drone Simulator with Video")
    print("----------------------------------")
    simulator = HeadlessDroneSimulatorWithVideo(
        listen_port=args.listen_port,
        control_ip=args.control_ip,
        control_port=args.control_port,
        video_port=args.video_port,
        verbose=args.verbose
    )
    
    try:
        simulator.start()
        # Keep the main thread alive
        while simulator.running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        simulator.stop()