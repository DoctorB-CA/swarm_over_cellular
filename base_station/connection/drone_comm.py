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

                # Start video streaming immediately after connecting
                if self.send_command("streamon"):
                    print("Video streaming started")
                else:
                    print("Warning: Failed to start video streaming")

                # Start telemetry receiver thread
                self.telemetry_thread = threading.Thread(target=self.receive_telemetry)
                self.telemetry_thread.daemon = True
                self.telemetry_thread.start()

                # Start FFmpeg video receiver thread
                self.video_thread = threading.Thread(target=self.receive_video_ffmpeg)
                self.video_thread.daemon = True
                self.video_thread.start()
                print(f"Video receive thread started: {self.video_thread.is_alive()}")

                self.connection_status_changed.emit(True, "Connected to drone")
                return True
            else:
                self.connection_status_changed.emit(False, "Failed to enter SDK mode")
                return False

        except Exception as e:
            self.connection_status_changed.emit(False, f"Connection error: {str(e)}")
            return False

    def setup_ffmpeg_pipeline(self):
        """Setup FFmpeg pipeline for raw drone video reception (UDP forwarded)"""
        try:
            # The UDP stream contains fragmented H.264 data that needs reassembly
            # Problem: Missing PPS headers cause initial decoding failures in WSL
            ffmpeg_cmd = [
                'ffmpeg',
                '-protocol_whitelist', 'file,udp',
                '-fflags', '+genpts+discardcorrupt+igndts',  # More tolerant parsing
                '-analyzeduration', '5000000',  # Analyze for 5 seconds (increased)
                '-probesize', '5000000',  # Probe 5MB of data (increased)
                '-f', 'h264',  # Raw H.264 from drone (forwarded by Pi)
                '-i', f'udp://0.0.0.0:{self.rtp_video_port}?fifo_size=2000000&overrun_nonfatal=1&buffer_size=2000000',
                '-vf', 'scale=640:480',  # Force scale to consistent size
                '-f', 'rawvideo',
                '-pix_fmt', 'rgb24',
                '-an',  # no audio
                '-loglevel', 'warning',  # Reduce log noise
                '-'     # output to stdout
            ]
            
            print(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
            
            # Start FFmpeg process
            self.ffmpeg_process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )
            
            print(f"FFmpeg process started for fragmented H.264 video on port {self.rtp_video_port}")
            print(f"FFmpeg PID: {self.ffmpeg_process.pid}")
            print("Waiting longer for H.264 headers to be found...")
            
            # Give FFmpeg much more time to find H.264 headers (especially in WSL)
            time.sleep(8.0)  # Increased to 8 seconds
            if self.ffmpeg_process.poll() is not None:
                stderr_output = self.ffmpeg_process.stderr.read().decode('utf-8')
                print(f"FFmpeg failed: {stderr_output}")
                return False
            else:
                print("FFmpeg process is running and should have found H.264 headers by now")
                # Check for any stderr output
                try:
                    import select
                    if select.select([self.ffmpeg_process.stderr], [], [], 0.5)[0]:
                        stderr_data = self.ffmpeg_process.stderr.read(4096).decode('utf-8', errors='ignore')
                        if stderr_data:
                            print(f"FFmpeg status:\n{stderr_data}")
                except:
                    pass
            
            return True
            
        except Exception as e:
            print(f"Error setting up FFmpeg pipeline: {e}")
            return False

    def receive_video_ffmpeg(self):
        """Receive and decode video frames using FFmpeg."""
        frame_width, frame_height = 640, 480
        frame_size = frame_width * frame_height * 3  # RGB24 bytes per frame
        
        print(f"Starting video receive thread, expecting frames of size {frame_size}")
        print(f"Thread started successfully: {threading.current_thread().name}")
        
        buf = b''
        frames_received = 0
        frames_emitted = 0
        no_data_count = 0
        last_stderr_check = time.time()
        
        while self.running and self.ffmpeg_process:
            # Debug: Check why loop might be ending
            if not self.running:
                print("Video thread ending: self.running is False")
                break
            if not self.ffmpeg_process:
                print("Video thread ending: ffmpeg_process is None")
                break
            # Check process health
            if self.ffmpeg_process.poll() is not None:
                stderr_output = self.ffmpeg_process.stderr.read().decode('utf-8')
                print(f"FFmpeg process ended. Error output: {stderr_output}")
                break
            
            # Check FFmpeg stderr periodically (every 2 seconds)
            current_time = time.time()
            if current_time - last_stderr_check > 2.0:
                try:
                    import select
                    if select.select([self.ffmpeg_process.stderr], [], [], 0)[0]:
                        stderr_data = self.ffmpeg_process.stderr.read(2048).decode('utf-8', errors='ignore')
                        if stderr_data:
                            print(f"FFmpeg stderr: {stderr_data}")
                except:
                    pass
                last_stderr_check = current_time
            
            # Read just what's needed to complete one frame
            needed = frame_size - len(buf)
            try:
                data = self.ffmpeg_process.stdout.read(needed)
            except Exception as e:
                print(f"Error reading from FFmpeg stdout: {e}")
                break
                
            if not data:
                no_data_count += 1
                if no_data_count % 1000 == 0:  # Every 5 seconds (1000 * 0.005)
                    print(f"No data from FFmpeg stdout for {no_data_count * 0.005:.1f} seconds")
                time.sleep(0.005)
                continue
            
            # Reset no-data counter when we get data
            no_data_count = 0
            buf += data
            
            # Only process when we have a full frame
            if len(buf) < frame_size:
                continue
            
            raw_frame, buf = buf[:frame_size], buf[frame_size:]
            frames_received += 1
            
            # Debug: Check frame data
            if frames_received == 1:
                print(f"First frame received: {len(raw_frame)} bytes")
                print(f"First 20 bytes: {raw_frame[:20].hex()}")
                # Check if frame is not all zeros (blank)
                non_zero_bytes = sum(1 for b in raw_frame[:1000] if b != 0)
                print(f"Non-zero bytes in first 1000: {non_zero_bytes}")
            
            if frames_received % 30 == 0:  # Log every 30 frames
                print(f"Received {frames_received} video frames, emitted {frames_emitted}")
            
            try:
                # Decode into NumPy and QImage
                frame_arr = np.frombuffer(raw_frame, np.uint8).reshape(frame_height, frame_width, 3)
                bytes_per_line = 3 * frame_width
                
                # Create QImage with explicit copy to ensure data persistence
                q_img = QImage(frame_arr.data, frame_width, frame_height,
                               bytes_per_line, QImage.Format_RGB888)
                
                # Force a copy to ensure the image data persists after the buffer is reused
                q_img_copy = q_img.copy()
                
                # Verify the image is valid
                if not q_img_copy.isNull():
                    # Emit the copied image
                    self.video_frame_received.emit(q_img_copy)
                    frames_emitted += 1
                    
                    # Debug first few frames
                    if frames_emitted <= 3:
                        print(f"Emitted frame {frames_emitted}: {q_img_copy.width()}x{q_img_copy.height()}, format: {q_img_copy.format()}")
                else:
                    print(f"Warning: Invalid QImage created for frame {frames_received}")
                    
            except Exception as e:
                print(f"Error processing frame {frames_received}: {e}")
                continue
            
        print(f"Video receive thread ended. Total frames received: {frames_received}, emitted: {frames_emitted}")

    def disconnect(self):
        """Disconnect from the drone"""
        print(f"disconnect() called. Current state - connected: {self.connected}, running: {self.running}")
        
        # Stop video streaming before disconnecting
        if self.connected:
            self.send_command("streamoff")
            print("Video streaming stopped")
        
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
