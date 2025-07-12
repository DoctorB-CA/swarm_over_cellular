#!/usr/bin/env python3
"""
Test script to display drone video directly on the Pi
This helps isolate if the issue is with drone->Pi or Pi->BaseStation
"""

import cv2
import socket
import threading
import time
import subprocess
import sys
from relay_config import DRONE_VIDEO_PORT, DRONE_IP, DRONE_COMMAND_PORT

class VideTester:
    def __init__(self):
        self.running = False
        self.cap = None
        self.command_socket = None
    
    def send_drone_command(self, command):
        """Send a command to the drone via UDP"""
        try:
            if not self.command_socket:
                self.command_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            print(f"Sending command to drone: '{command}'")
            self.command_socket.sendto(command.encode(), (DRONE_IP, DRONE_COMMAND_PORT))
            
            # Wait a bit for drone to process command
            time.sleep(0.5)
            return True
            
        except Exception as e:
            print(f"✗ ERROR sending command '{command}': {e}")
            return False
    
    def initialize_drone(self):
        """Initialize drone and start video streaming"""
        print("=== DRONE INITIALIZATION ===")
        print(f"Connecting to drone at {DRONE_IP}:{DRONE_COMMAND_PORT}")
        
        # Send required commands to drone
        commands = [
            "command",    # Enter SDK mode
            "streamon"    # Start video streaming
        ]
        
        success = True
        for cmd in commands:
            if not self.send_drone_command(cmd):
                success = False
                break
            print(f"✓ Command '{cmd}' sent successfully")
        
        if success:
            print("✓ Drone initialized - video streaming should now be active")
            print("Waiting 3 seconds for video stream to stabilize...")
            time.sleep(3)
        else:
            print("✗ Failed to initialize drone")
        
        return success
        
    def test_opencv_direct(self):
        """Test 1: Try to capture video directly with OpenCV"""
        print("=== TEST 1: OpenCV Direct Capture ===")
        
        # Try different video sources
        sources = [
            f"udp://0.0.0.0:{DRONE_VIDEO_PORT}",
            f"udp://{DRONE_IP}:{DRONE_VIDEO_PORT}",
            0,  # Default camera
            1   # USB camera
        ]
        
        for i, source in enumerate(sources):
            print(f"Trying source {i+1}: {source}")
            try:
                cap = cv2.VideoCapture(source)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret:
                        print(f"✓ SUCCESS: Got frame from {source}")
                        print(f"  Frame shape: {frame.shape}")
                        
                        # Save a test frame
                        cv2.imwrite(f"/tmp/test_frame_{i}.jpg", frame)
                        print(f"  Saved test frame to /tmp/test_frame_{i}.jpg")
                        
                        # Try to show a few frames
                        for j in range(5):
                            ret, frame = cap.read()
                            if ret:
                                print(f"  Frame {j+1}: {frame.shape}")
                            else:
                                print(f"  Frame {j+1}: Failed to read")
                                break
                        
                        cap.release()
                        return True
                    else:
                        print(f"✗ FAILED: Could not read frame from {source}")
                else:
                    print(f"✗ FAILED: Could not open {source}")
                cap.release()
            except Exception as e:
                print(f"✗ ERROR with {source}: {e}")
        
        return False
    
    def test_ffmpeg_display(self):
        """Test 2: Use FFmpeg to display video"""
        print("\n=== TEST 2: FFmpeg Video Display ===")
        
        # FFmpeg command to receive and display video
        ffmpeg_cmd = [
            'ffmpeg',
            '-f', 'h264',
            '-i', f'udp://0.0.0.0:{DRONE_VIDEO_PORT}?fifo_size=1000000&overrun_nonfatal=1',
            '-f', 'sdl2',  # SDL display
            '-'
        ]
        
        print(f"Running: {' '.join(ffmpeg_cmd)}")
        print("Press 'q' in the video window to quit, or Ctrl+C here")
        
        try:
            process = subprocess.run(ffmpeg_cmd, timeout=30)
            print(f"FFmpeg exited with code: {process.returncode}")
        except subprocess.TimeoutExpired:
            print("FFmpeg timeout after 30 seconds")
        except KeyboardInterrupt:
            print("Interrupted by user")
        except Exception as e:
            print(f"FFmpeg error: {e}")
    
    def test_ffmpeg_save(self):
        """Test 3: Use FFmpeg to save video to file"""
        print("\n=== TEST 3: FFmpeg Save to File ===")
        
        output_file = "/tmp/drone_video_test.mp4"
        
        ffmpeg_cmd = [
            'ffmpeg',
            '-f', 'h264',
            '-i', f'udp://0.0.0.0:{DRONE_VIDEO_PORT}?fifo_size=1000000&overrun_nonfatal=1',
            '-t', '10',  # Record for 10 seconds
            '-c', 'copy',  # Don't re-encode
            output_file,
            '-y'  # Overwrite output file
        ]
        
        print(f"Recording 10 seconds to {output_file}")
        print(f"Command: {' '.join(ffmpeg_cmd)}")
        
        try:
            result = subprocess.run(ffmpeg_cmd, 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=15)
            
            if result.returncode == 0:
                print(f"✓ SUCCESS: Video saved to {output_file}")
                # Check file size
                try:
                    import os
                    size = os.path.getsize(output_file)
                    print(f"  File size: {size} bytes")
                    if size > 1000:
                        print("  File has content - video reception appears to work!")
                    else:
                        print("  File is very small - might be empty")
                except:
                    pass
            else:
                print(f"✗ FAILED: FFmpeg exited with code {result.returncode}")
                print(f"  stderr: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print("✗ TIMEOUT: No video received in 15 seconds")
        except Exception as e:
            print(f"✗ ERROR: {e}")
    
    def test_packet_capture(self):
        """Test 4: Check if we're receiving any packets on video port"""
        print(f"\n=== TEST 4: Packet Capture on Port {DRONE_VIDEO_PORT} ===")
        
        def packet_listener():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('0.0.0.0', DRONE_VIDEO_PORT))
                sock.settimeout(1.0)
                
                print(f"Listening for packets on port {DRONE_VIDEO_PORT}...")
                packet_count = 0
                total_bytes = 0
                
                start_time = time.time()
                while time.time() - start_time < 10:  # Listen for 10 seconds
                    try:
                        data, addr = sock.recvfrom(65536)
                        packet_count += 1
                        total_bytes += len(data)
                        
                        if packet_count <= 5:  # Show details for first 5 packets
                            print(f"  Packet {packet_count}: {len(data)} bytes from {addr}")
                            # Show first few bytes as hex
                            hex_data = ' '.join(f'{b:02x}' for b in data[:16])
                            print(f"    First 16 bytes: {hex_data}")
                    
                    except socket.timeout:
                        continue
                    except Exception as e:
                        print(f"  Error receiving packet: {e}")
                        break
                
                sock.close()
                
                if packet_count > 0:
                    print(f"✓ SUCCESS: Received {packet_count} packets, {total_bytes} total bytes")
                    print(f"  Average packet size: {total_bytes/packet_count:.1f} bytes")
                    return True
                else:
                    print(f"✗ FAILED: No packets received in 10 seconds")
                    return False
                    
            except Exception as e:
                print(f"✗ ERROR setting up packet capture: {e}")
                return False
    
    def cleanup_drone(self):
        """Stop video streaming and close connections"""
        print("\n=== DRONE CLEANUP ===")
        self.send_drone_command("streamoff")
        if self.command_socket:
            self.command_socket.close()
        print("✓ Drone video streaming stopped")

def main():
    print("Drone Video Test Suite")
    print("=" * 50)
    print(f"Testing video reception from drone at {DRONE_IP}")
    print(f"Video port: {DRONE_VIDEO_PORT}, Command port: {DRONE_COMMAND_PORT}")
    print()
    
    tester = VideTester()
    
    try:
        # Initialize drone and start video streaming
        if not tester.initialize_drone():
            print("Failed to initialize drone - aborting tests")
            return
        
        # Run all tests
        results = []
        
        # Test 4 first - check if we're getting any data
        results.append(("Packet Capture", tester.test_packet_capture()))
        
        # Test 3 - Save to file (non-interactive)
        results.append(("FFmpeg Save", tester.test_ffmpeg_save()))
        
        # Test 1 - OpenCV
        results.append(("OpenCV", tester.test_opencv_direct()))
        
        # Test 2 - FFmpeg display (commented out as it requires display)
        # print("\nSkipping FFmpeg display test (requires X11 display)")
        
        print("\n" + "=" * 50)
        print("TEST SUMMARY:")
        for test_name, success in results:
            status = "✓ PASS" if success else "✗ FAIL"
            print(f"  {test_name}: {status}")
        
        print("\nNext steps:")
        if results[0][1]:  # Packet capture worked
            print("- Video packets are being received from drone")
            if results[1][1]:  # FFmpeg save worked
                print("- FFmpeg can decode the video stream")
                print("- Issue is likely in the Pi->BaseStation relay")
            else:
                print("- Video packets received but FFmpeg can't decode them")
                print("- Check drone video format/codec")
        else:
            print("- No video packets received from drone")
            print("- Check drone IP, video streaming settings, and network connectivity")
    
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    finally:
        # Always cleanup
        tester.cleanup_drone()

if __name__ == '__main__':
    main()