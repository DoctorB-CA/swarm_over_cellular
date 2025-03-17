import socket
import threading
import json
import struct
import numpy as np
import cv2
from PyQt5.QtCore import QObject, pyqtSignal, Qt
from PyQt5.QtGui import QImage

# Import network configuration
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from connection.network_config import DRONE_IP, COMMAND_PORT, TELEMETRY_PORT, VIDEO_PORT, SOCKET_TIMEOUT

class DroneComm(QObject):
    """Communication layer for the drone - separated from the GUI"""

    # Signals for communication between threads and GUI
    telemetry_received = pyqtSignal(dict)
    video_frame_received = pyqtSignal(QImage)
    connection_status_changed = pyqtSignal(bool, str)

    def __init__(self, ip=DRONE_IP, command_port=COMMAND_PORT, telemetry_port=TELEMETRY_PORT, video_port=VIDEO_PORT):
        super().__init__()
        self.ip = ip
        self.command_port = command_port
        self.telemetry_port = telemetry_port
        self.video_port = video_port
        self.command_socket = None
        self.telemetry_socket = None
        self.video_socket = None
        self.connected = False
        self.running = False

        # Threads
        self.telemetry_thread = None
        self.video_thread = None

    def connect(self):
        """Connect to the drone"""
        try:
            # Create command socket
            self.command_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # Create telemetry socket
            self.telemetry_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.telemetry_socket.bind(("0.0.0.0", self.telemetry_port))
            
            # Create video socket
            self.video_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.video_socket.bind(("0.0.0.0", self.video_port))

            # Enter SDK mode
            if self.send_command("command"):
                self.connected = True
                self.running = True

                # Start telemetry receiver thread
                self.telemetry_thread = threading.Thread(target=self.receive_telemetry)
                self.telemetry_thread.daemon = True
                self.telemetry_thread.start()
                
                # Start video receiver thread
                self.video_thread = threading.Thread(target=self.receive_video)
                self.video_thread.daemon = True
                self.video_thread.start()

                self.connection_status_changed.emit(True, "Connected to drone")
                return True
            else:
                self.connection_status_changed.emit(False, "Failed to enter SDK mode")
                return False

        except Exception as e:
            self.connection_status_changed.emit(False, f"Connection error: {str(e)}")
            return False

    def disconnect(self):
        """Disconnect from the drone"""
        self.running = False
        self.connected = False

        # Wait for threads to finish
        if self.telemetry_thread and self.telemetry_thread.is_alive():
            self.telemetry_thread.join(timeout=1.0)
            
        if self.video_thread and self.video_thread.is_alive():
            self.video_thread.join(timeout=1.0)

        # Close sockets
        if self.command_socket:
            self.command_socket.close()
            self.command_socket = None

        if self.telemetry_socket:
            self.telemetry_socket.close()
            self.telemetry_socket = None
            
        if self.video_socket:
            self.video_socket.close()
            self.video_socket = None

        self.connection_status_changed.emit(False, "Disconnected")

    def send_command(self, command):
        """Send a command to the drone"""
        if not self.connected and command != "command":
            return False

        try:
            if self.command_socket:
                self.command_socket.sendto(command.encode(), (self.ip, self.command_port))
                return True
        except Exception as e:
            print(f"Command error: {e}")
            return False

    def receive_telemetry(self):
        """Receive telemetry data from the drone"""
        self.telemetry_socket.settimeout(SOCKET_TIMEOUT)  # timeout for clean shutdown

        while self.running:
            try:
                data, _ = self.telemetry_socket.recvfrom(4096)

                try:
                    # Parse JSON telemetry data
                    telemetry = json.loads(data.decode('utf-8'))
                    self.telemetry_received.emit(telemetry)

                except json.JSONDecodeError:
                    print("Error decoding telemetry data")

            except socket.timeout:
                # This is just to allow for clean shutdown
                pass
            except Exception as e:
                print(f"Telemetry receive error: {e}")
                if not self.running:
                    break
                    
    def receive_video(self):
        """Receive video frames from the drone"""
        self.video_socket.settimeout(SOCKET_TIMEOUT)  # timeout for clean shutdown
        
        while self.running:
            try:
                # Receive video data
                data, _ = self.video_socket.recvfrom(65536)  # Use larger buffer for video
                
                if len(data) < 2:
                    continue  # Skip too small packets
                    
                try:
                    # Extract header length from first 2 bytes
                    header_length = int.from_bytes(data[0:2], byteorder='big')
                    
                    # Extract header and image data
                    header_end = 2 + header_length
                    header = data[2:header_end].decode()
                    image_data = data[header_end:]
                    
                    # Parse header (frame number and timestamp)
                    frame_number, timestamp = header.split(':', 1)
                    
                    # Decode JPEG image
                    np_arr = np.frombuffer(image_data, np.uint8)
                    cv_img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                    
                    if cv_img is None:
                        print("Error decoding image data")
                        continue
                    
                    # Convert OpenCV image (BGR) to Qt image (RGB)
                    height, width, channels = cv_img.shape
                    bytes_per_line = channels * width
                    
                    # Convert BGR to RGB
                    cv_img_rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
                    
                    # Create QImage (make a deep copy to ensure thread safety)
                    q_img = QImage(cv_img_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888).copy()
                    
                    # Emit signal with the frame
                    self.video_frame_received.emit(q_img)
                    
                except Exception as e:
                    print(f"Error processing video frame: {e}")
                
            except socket.timeout:
                # This is just to allow for clean shutdown
                pass
            except Exception as e:
                print(f"Video receive error: {e}")
                if not self.running:
                    break
