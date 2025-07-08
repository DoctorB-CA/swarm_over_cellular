import socket
import threading
import json
import struct
import numpy as np
import cv2
import subprocess
import time
from PyQt5.QtCore import QObject, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QImage

# Import network configuration
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from connection.network_config import DRONE_IP, COMMAND_PORT, TELEMETRY_PORT, VIDEO_PORT, RTP_VIDEO_PORT, SOCKET_TIMEOUT

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
        self.rtp_video_port = RTP_VIDEO_PORT
        self.command_socket = None
        self.telemetry_socket = None
        self.connected = False
        self.running = False

        # FFmpeg process for RTP video
        self.ffmpeg_process = None
        self.video_thread = None

        # Threads
        self.telemetry_thread = None

    def connect(self):
        """Connect to the drone"""
        try:
            # Create command socket
            self.command_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # Create telemetry socket
            self.telemetry_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.telemetry_socket.bind(("0.0.0.0", self.telemetry_port))

            # Setup FFmpeg RTP video pipeline
            if not self.setup_ffmpeg_pipeline():
                self.connection_status_changed.emit(False, "Failed to setup video pipeline")
                return False

            # Enter SDK mode
            if self.send_command("command"):
                self.connected = True
                self.running = True

                # Start telemetry receiver thread
                self.telemetry_thread = threading.Thread(target=self.receive_telemetry)
                self.telemetry_thread.daemon = True
                self.telemetry_thread.start()

                # Start FFmpeg video receiver thread
                self.video_thread = threading.Thread(target=self.receive_video_ffmpeg)
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

    def setup_ffmpeg_pipeline(self):
        """Setup FFmpeg pipeline for RTP H.264 video reception"""
        try:
            # FFmpeg command to receive RTP H.264 and output raw RGB frames
            ffmpeg_cmd = [
                'ffmpeg',
                '-protocol_whitelist', 'file,udp,rtp',
                '-i', f'rtp://127.0.0.1:{self.rtp_video_port}',
                '-f', 'rawvideo',
                '-pix_fmt', 'rgb24',
                '-an',  # no audio
                '-'     # output to stdout
            ]
            
            # Start FFmpeg process
            self.ffmpeg_process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )
            
            print(f"FFmpeg process started for RTP video on port {self.rtp_video_port}")
            return True
            
        except Exception as e:
            print(f"Error setting up FFmpeg pipeline: {e}")
            return False

    def receive_video_ffmpeg(self):
        """Receive and decode video frames using FFmpeg."""
        # Launch FFmpeg elsewhere with:
        # ffmpeg -i udp://0.0.0.0:11111 -f rawvideo -pix_fmt rgb24 -s 640x480 -an -sn pipe:1
        frame_width, frame_height = 640, 480
        frame_size = frame_width * frame_height * 3  # RGB24 bytes per frame
        
        buf = b''
        while self.running and self.ffmpeg_process:
            # Check process health
            if self.ffmpeg_process.poll() is not None:
                break
            
            # Read just what's needed to complete one frame
            needed = frame_size - len(buf)
            data = self.ffmpeg_process.stdout.read(needed)
            if not data:
                time.sleep(0.005)
                continue
            buf += data
            
            # Only process when we have a full frame
            if len(buf) < frame_size:
                continue
            
            raw_frame, buf = buf[:frame_size], buf[frame_size:]
            
            # Decode into NumPy and QImage
            frame_arr = np.frombuffer(raw_frame, np.uint8).reshape(frame_height, frame_width, 3)
            bytes_per_line = 3 * frame_width
            q_img = QImage(frame_arr.data, frame_width, frame_height,
                           bytes_per_line, QImage.Format_RGB888)
            
            # Emit without forcing a copy; Qt will take its own ref
            self.video_frame_received.emit(q_img)

    def disconnect(self):
        """Disconnect from the drone"""
        self.running = False
        self.connected = False

        # Stop FFmpeg process
        if self.ffmpeg_process:
            try:
                self.ffmpeg_process.terminate()
                self.ffmpeg_process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self.ffmpeg_process.kill()
            except Exception as e:
                print(f"Error stopping FFmpeg process: {e}")
            finally:
                self.ffmpeg_process = None

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
        """Legacy video receive method - now handled by GStreamer"""
        # This method is no longer used but kept for compatibility
        pass
