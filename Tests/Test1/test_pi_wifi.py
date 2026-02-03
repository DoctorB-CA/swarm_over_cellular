#!/usr/bin/env python3
"""
Pi Test Script - WiFi Hotspot (No Cellular/Wireguard)
Receives Tello video and forwards as RTP to PC over WiFi
"""

import socket
import time
import subprocess

# Configuration for WiFi hotspot test
TELLO_IP = "192.168.10.1"
TELLO_PORT = 8889
PI_IP = "0.0.0.0"  # Listen on all interfaces
PI_PORT = 8889

# PC IP on WiFi network
PC_IP = "10.160.77.127"  # PC's IP
VIDEO_PORT = 11111

def main():
    print(f"\n{'='*60}")
    print(f"PI TEST - WIFI HOTSPOT MODE")
    print(f"{'='*60}")
    print(f"Tello: {TELLO_IP}:{TELLO_PORT}")
    print(f"PC: {PC_IP}:{VIDEO_PORT}")
    print(f"{'='*60}\n")
    
    # Create socket for Tello commands
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((PI_IP, PI_PORT))
    
    # Initialize Tello
    print("[INIT] Sending 'command' to Tello...")
    sock.sendto("command".encode('utf-8'), (TELLO_IP, TELLO_PORT))
    time.sleep(2)
    
    # Start video stream
    print("[VIDEO] Sending 'streamon' to Tello...")
    sock.sendto("streamon".encode('utf-8'), (TELLO_IP, TELLO_PORT))
    time.sleep(2)
    
    # Start ffmpeg to forward video
    print(f"[VIDEO] Starting ffmpeg: Tello UDP -> PC UDP...")
    print(f"[VIDEO] Command: ffmpeg -i udp://0.0.0.0:11111 -c:v copy -f mpegts udp://{PC_IP}:{VIDEO_PORT}")
    
    # Run ffmpeg as subprocess
    ffmpeg_cmd = [
        "ffmpeg",
        "-i", "udp://0.0.0.0:11111",
        "-c:v", "copy",  # Copy H.264 without transcoding
        "-f", "mpegts",  # MPEG-TS container for UDP streaming
        f"udp://{PC_IP}:{VIDEO_PORT}"
    ]
    
    ffmpeg_process = subprocess.Popen(ffmpeg_cmd)
    
    print("\n[READY] Video forwarding active. Press Ctrl+C to stop.\n")
    
    try:
        # Keep alive loop
        while True:
            time.sleep(5)
            sock.sendto("command".encode('utf-8'), (TELLO_IP, TELLO_PORT))
            print("[KEEP-ALIVE] Sent")
    
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Stopping...")
        sock.sendto("streamoff".encode('utf-8'), (TELLO_IP, TELLO_PORT))
        ffmpeg_process.terminate()
        sock.close()
        print("[SHUTDOWN] Done")

if __name__ == "__main__":
    main()
