#!/usr/bin/env python3
"""
Test Pi to Base Station video relay
Since we confirmed Pi can receive video from drone, now test the relay part
"""

import cv2
import socket
import time
import subprocess
import threading
from relay_config import *

class VideoRelayTester:
    def __init__(self):
        self.running = False
        self.drone_socket = None
        self.base_socket = None
        
    def send_drone_command(self, command):
        """Send command to drone"""
        try:
            cmd_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            cmd_socket.sendto(command.encode(), (DRONE_IP, DRONE_COMMAND_PORT))
            cmd_socket.close()
            print(f"✓ Sent command: {command}")
            time.sleep(0.5)
            return True
        except Exception as e:
            print(f"✗ Failed to send command: {e}")
            return False
    
    def test_simple_udp_relay(self):
        """Test 1: Simple UDP packet forwarding (current Pi relay)"""
        print("=== TEST 1: Simple UDP Relay ===")
        print(f"Relay: {DRONE_IP}:{DRONE_VIDEO_PORT} -> {BASE_STATION_IP}:{BASE_STATION_VIDEO_PORT}")
        
        try:
            # Socket to receive from drone
            self.drone_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.drone_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.drone_socket.bind(('0.0.0.0', DRONE_VIDEO_PORT))
            self.drone_socket.settimeout(1.0)
            
            # Socket to send to base station
            self.base_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            print("Starting UDP relay...")
            packet_count = 0
            bytes_relayed = 0
            
            # Start drone video
            self.send_drone_command("command")
            self.send_drone_command("streamon")
            
            start_time = time.time()
            while time.time() - start_time < 15:  # Relay for 15 seconds
                try:
                    # Receive from drone
                    data, addr = self.drone_socket.recvfrom(65536)
                    
                    # Forward to base station
                    self.base_socket.sendto(data, (BASE_STATION_IP, BASE_STATION_VIDEO_PORT))
                    
                    packet_count += 1
                    bytes_relayed += len(data)
                    
                    if packet_count <= 5:
                        print(f"  Relayed packet {packet_count}: {len(data)} bytes")
                    elif packet_count % 50 == 0:
                        print(f"  Relayed {packet_count} packets, {bytes_relayed} bytes total")
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"  Relay error: {e}")
                    break
            
            # Stop drone video
            self.send_drone_command("streamoff")
            
            if packet_count > 0:
                print(f"✓ SUCCESS: Relayed {packet_count} packets, {bytes_relayed} bytes")
                print(f"  Average packet size: {bytes_relayed/packet_count:.1f} bytes")
                return True
            else:
                print("✗ FAILED: No packets relayed")
                return False
                
        except Exception as e:
            print(f"✗ ERROR: {e}")
            return False
        finally:
            if self.drone_socket:
                self.drone_socket.close()
            if self.base_socket:
                self.base_socket.close()
    
    def test_ffmpeg_rtp_relay(self):
        """Test 2: FFmpeg RTP relay"""
        print("\n=== TEST 2: FFmpeg RTP Relay ===")
        
        # Start drone video
        self.send_drone_command("command")
        self.send_drone_command("streamon")
        time.sleep(2)
        
        # FFmpeg command to relay as RTP
        ffmpeg_cmd = [
            'ffmpeg',
            '-f', 'h264',
            '-i', f'udp://0.0.0.0:{DRONE_VIDEO_PORT}?fifo_size=1000000&overrun_nonfatal=1',
            '-c', 'copy',
            '-f', 'rtp',
            f'rtp://{BASE_STATION_IP}:{BASE_STATION_VIDEO_PORT}?pkt_size=1400'
        ]
        
        print(f"Command: {' '.join(ffmpeg_cmd)}")
        print("Running FFmpeg RTP relay for 10 seconds...")
        
        try:
            process = subprocess.run(ffmpeg_cmd, 
                                   capture_output=True, 
                                   text=True, 
                                   timeout=12)
            
            if process.returncode == 0:
                print("✓ SUCCESS: FFmpeg RTP relay completed")
                return True
            else:
                print(f"✗ FAILED: FFmpeg exited with code {process.returncode}")
                print(f"  stderr: {process.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("✓ SUCCESS: FFmpeg ran for full duration (timeout expected)")
            return True
        except Exception as e:
            print(f"✗ ERROR: {e}")
            return False
        finally:
            self.send_drone_command("streamoff")
    
    def test_opencv_to_udp(self):
        """Test 3: OpenCV capture and UDP forward"""
        print("\n=== TEST 3: OpenCV to UDP ===")
        
        try:
            # Start drone video
            self.send_drone_command("command")
            self.send_drone_command("streamon")
            time.sleep(2)
            
            # Open video capture
            cap = cv2.VideoCapture(f'udp://0.0.0.0:{DRONE_VIDEO_PORT}')
            if not cap.isOpened():
                print("✗ FAILED: Could not open video capture")
                return False
            
            # Socket to send to base station
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            frame_count = 0
            start_time = time.time()
            
            print("Capturing and forwarding frames...")
            while time.time() - start_time < 10:  # Run for 10 seconds
                ret, frame = cap.read()
                if ret:
                    # Convert frame to bytes (simple JPEG encoding)
                    _, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
                    frame_data = encoded.tobytes()
                    
                    # Send to base station (split if too large)
                    max_size = 1400
                    for i in range(0, len(frame_data), max_size):
                        chunk = frame_data[i:i+max_size]
                        sock.sendto(chunk, (BASE_STATION_IP, BASE_STATION_VIDEO_PORT))
                    
                    frame_count += 1
                    if frame_count % 30 == 0:
                        print(f"  Sent {frame_count} frames")
                
            cap.release()
            sock.close()
            self.send_drone_command("streamoff")
            
            if frame_count > 0:
                print(f"✓ SUCCESS: Sent {frame_count} frames as JPEG over UDP")
                return True
            else:
                print("✗ FAILED: No frames captured")
                return False
                
        except Exception as e:
            print(f"✗ ERROR: {e}")
            return False

def main():
    print("Video Relay Test Suite")
    print("=" * 50)
    print(f"Testing video relay from Pi to Base Station")
    print(f"Drone: {DRONE_IP}:{DRONE_VIDEO_PORT}")
    print(f"Base Station: {BASE_STATION_IP}:{BASE_STATION_VIDEO_PORT}")
    print()
    
    tester = VideoRelayTester()
    results = []
    
    try:
        # Test simple UDP relay (what the current Pi does)
        results.append(("Simple UDP Relay", tester.test_simple_udp_relay()))
        
        # Test FFmpeg RTP relay (better approach)
        results.append(("FFmpeg RTP Relay", tester.test_ffmpeg_rtp_relay()))
        
        # Test OpenCV method (alternative)
        results.append(("OpenCV to UDP", tester.test_opencv_to_udp()))
        
        print("\n" + "=" * 50)
        print("RELAY TEST SUMMARY:")
        for test_name, success in results:
            status = "✓ PASS" if success else "✗ FAIL"
            print(f"  {test_name}: {status}")
        
        print("\nRecommendations:")
        if results[1][1]:  # FFmpeg RTP worked
            print("- Use FFmpeg RTP relay for best results")
            print("- Update Pi service to use drone_relay_rtp.py")
        elif results[0][1]:  # Simple UDP worked
            print("- Simple UDP relay works but may have format issues")
            print("- Base station needs to handle raw drone video format")
        else:
            print("- Check network connectivity between Pi and Base Station")
            print("- Verify Base Station IP and firewall settings")
    
    except KeyboardInterrupt:
        print("\nTest interrupted by user")

if __name__ == '__main__':
    main()