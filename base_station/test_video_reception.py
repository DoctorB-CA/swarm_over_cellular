#!/usr/bin/env python3
"""
Test video reception on base station
Run this while the Pi relay test is running
"""

import socket
import time
import subprocess
import threading
from connection.network_config import RTP_VIDEO_PORT

def test_packet_reception():
    """Test if we're receiving packets on video port"""
    print(f"=== Testing packet reception on port {RTP_VIDEO_PORT} ===")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', RTP_VIDEO_PORT))
        sock.settimeout(1.0)
        
        print(f"Listening for packets on port {RTP_VIDEO_PORT}...")
        print("Run the Pi relay test now!")
        print("Press Ctrl+C to stop")
        
        packet_count = 0
        total_bytes = 0
        last_report = time.time()
        
        while True:
            try:
                data, addr = sock.recvfrom(65536)
                packet_count += 1
                total_bytes += len(data)
                
                # Report every 5 seconds
                if time.time() - last_report >= 5:
                    print(f"Received {packet_count} packets, {total_bytes} bytes from {addr}")
                    
                    # Show first few bytes of recent packet
                    hex_data = ' '.join(f'{b:02x}' for b in data[:16])
                    print(f"  Latest packet: {len(data)} bytes, starts with: {hex_data}")
                    
                    last_report = time.time()
                    
            except socket.timeout:
                continue
                
    except KeyboardInterrupt:
        print(f"\nFinal stats: {packet_count} packets, {total_bytes} bytes received")
        if packet_count > 0:
            print(f"Average packet size: {total_bytes/packet_count:.1f} bytes")
            print("✓ Video packets are reaching the base station!")
        else:
            print("✗ No video packets received")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        sock.close()

def test_ffmpeg_reception():
    """Test FFmpeg video reception and save"""
    print(f"\n=== Testing FFmpeg reception on port {RTP_VIDEO_PORT} ===")
    
    output_file = "/tmp/received_video_test.mp4"
    
    # Try RTP format first
    ffmpeg_cmd = [
        'ffmpeg',
        '-protocol_whitelist', 'file,udp,rtp',
        '-f', 'rtp',
        '-i', f'rtp://0.0.0.0:{RTP_VIDEO_PORT}',
        '-t', '10',  # Record for 10 seconds
        '-c', 'copy',
        output_file,
        '-y'
    ]
    
    print(f"Command: {' '.join(ffmpeg_cmd)}")
    print("Recording 10 seconds of video...")
    print("Make sure Pi relay test is running!")
    
    try:
        result = subprocess.run(ffmpeg_cmd, 
                              capture_output=True, 
                              text=True, 
                              timeout=15)
        
        if result.returncode == 0:
            print(f"✓ SUCCESS: Video saved to {output_file}")
            
            # Check file size
            import os
            if os.path.exists(output_file):
                size = os.path.getsize(output_file)
                print(f"  File size: {size} bytes")
                if size > 1000:
                    print("  ✓ File has content - video reception works!")
                else:
                    print("  ✗ File is very small - may be empty")
        else:
            print(f"✗ FAILED: FFmpeg exited with code {result.returncode}")
            print(f"  stderr: {result.stderr}")
            
            # Try raw H.264 fallback
            print("\nTrying raw H.264 format...")
            ffmpeg_cmd[3] = 'h264'
            ffmpeg_cmd[5] = f'udp://0.0.0.0:{RTP_VIDEO_PORT}?fifo_size=1000000&overrun_nonfatal=1'
            
            result = subprocess.run(ffmpeg_cmd, 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=15)
            
            if result.returncode == 0:
                print("✓ SUCCESS with H.264 format")
            else:
                print(f"✗ H.264 format also failed: {result.stderr}")
                
    except subprocess.TimeoutExpired:
        print("✗ TIMEOUT: No video received in time")
    except Exception as e:
        print(f"✗ ERROR: {e}")

if __name__ == '__main__':
    print("Base Station Video Reception Test")
    print("=" * 50)
    print("Run this BEFORE starting the Pi relay test")
    print()
    
    choice = input("Test (1) Packet reception or (2) FFmpeg reception? [1/2]: ").strip()
    
    if choice == '2':
        test_ffmpeg_reception()
    else:
        test_packet_reception()