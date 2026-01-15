#!/usr/bin/env python3
"""
Raspberry Pi Middleman for Tello Drone Control
Receives commands from PC and forwards to Tello drone
Receives responses from drone and forwards back to PC
Forwards video stream from Tello to PC
"""

import socket
import select
import threading
import time
import netifaces
from typing import Optional, Tuple

# Type alias
Addr = Tuple[str, int]

# get the ip of the drone (well actuly the pi in the mesh)
def get_bat0_ip():
    """Get IP address from bat0 interface"""
    try:
        addrs = netifaces.ifaddresses('bat0')
        ip = addrs[netifaces.AF_INET][0]['addr']
        return ip
    except Exception as e:
        print(f"[ERROR] Could not get bat0 IP: {e}")
        print("[ERROR] Falling back to default 10.0.0.1")
        return "10.0.0.1"
# drone number 2 is 10.0.0.2 easy
def get_drone_number_from_ip(ip):
    """Extract drone number from last octet of IP (x.x.x.y -> y)"""
    try:
        last_octet = int(ip.split('.')[-1])
        return last_octet
    except Exception as e:
        print(f"[ERROR] Could not parse drone number from IP {ip}: {e}")
        print("[ERROR] Falling back to drone number 1")
        return 1

# Auto-detect configuration at startup
PI_IP = get_bat0_ip()
DRONE_NUMBER = get_drone_number_from_ip(PI_IP)

# ============================
# HARD-CODED CONFIG
# ============================
LISTEN_IP = "0.0.0.0"      # Listen on all interfaces
LISTEN_PORT = 20002        # PC -> PI port

TELLO_IP = "192.168.10.1"
TELLO_PORT = 8889
TELLO_DEV = "wlan1"        # Force tello traffic out wlan1

VIDEO_PORT = 11110 + DRONE_NUMBER  # Each drone uses different port (11111, 11112, 11113...)
TELLO_VIDEO_PORT = 11111  # Tello video stream port

SO_BINDTODEVICE = 25 # ?

# Global variables
last_pc_addr = None  # Track PC address for video forwarding : make pc addr to globel. not hard coded.

# creating soket to pc. dah
def create_pc_socket() -> socket.socket:
    """Create socket to listen for PC commands"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((LISTEN_IP, LISTEN_PORT))
    return s
#creating socket to the drone
def create_tello_socket() -> socket.socket:
    """Create socket for Tello communication - bound to wlan1 interface"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Force tello traffic out wlan1 (needs sudo)
    s.setsockopt(socket.SOL_SOCKET, SO_BINDTODEVICE, TELLO_DEV.encode() + b"\0")
    s.bind(("0.0.0.0", 0))
    return s


# ----- main loop ------------
def forward_loop(s_pc: socket.socket, s_tello: socket.socket) -> None:
    """Main forwarding loop - bidirectional PC <-> Tello"""
    global last_pc_addr
    
    print(f"[Pi] listen {LISTEN_IP}:{LISTEN_PORT}")
    print(f"[Pi] tello {TELLO_IP}:{TELLO_PORT} via {TELLO_DEV}")
    
    while True:
        # Wait for data on either socket
        readable, _, _ = select.select([s_pc, s_tello], [], [], 1.0) # _,_,_, = read_socks, write_socks, ready-to-write
        
        for sock in readable:
            if sock == s_pc:
                # Data from PC -> forward to Tello
                data, addr = s_pc.recvfrom(1024)
                last_pc_addr = addr  # Save PC address for video forwarding
                command = data.decode('utf-8', errors='ignore')
                print(f"[PC -> PI] {addr}: {command}")
                s_tello.sendto(data, (TELLO_IP, TELLO_PORT))
                print(f"[PI -> TELLO] Forwarded: {command}")
                
            elif sock == s_tello:
                # Data from Tello -> forward to PC
                data, addr = s_tello.recvfrom(1024)
                response = data.decode('utf-8', errors='ignore')
                print(f"[TELLO -> PI] Received: {response}")
                if last_pc_addr:
                    s_pc.sendto(data, last_pc_addr)
                    print(f"[PI -> PC] Forwarded to {last_pc_addr}: {response}")
# ----------------------------------

#video thread
def forward_video():
    """
    Simple UDP forwarding: Tello video -> PC port 11111
    Just forwards raw UDP packets as-is
    """
    global last_pc_addr
    
    print("[VIDEO] Video forwarding thread started")
    
    # Create socket for receiving video from Tello
    video_receive_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    video_receive_sock.bind(('', TELLO_VIDEO_PORT))
    
    # Create socket for sending video to PC
    video_send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    print(f"[VIDEO] Listening for Tello video on port {TELLO_VIDEO_PORT}")
    print(f"[VIDEO] Will forward to PC on port {VIDEO_PORT}")
    
    packet_count = 0
    
    while True:
        try:
            # Receive video packet from Tello
            data, addr = video_receive_sock.recvfrom(2048)
            
            packet_count += 1
            if packet_count % 100 == 0:
                print(f"[VIDEO] Forwarded {packet_count} packets")
            
            # Forward to PC if we know PC address
            if last_pc_addr:
                video_addr = (last_pc_addr[0], VIDEO_PORT)
                video_send_sock.sendto(data, video_addr)
                
        except Exception as e:
            print(f"[VIDEO ERROR] {e}")
            time.sleep(0.1)

def main():
    # -- printing -- 
    print(f"{'='*60}")
    print(f"PI MIDDLEMAN - COMMANDS & VIDEO")
    print(f"{'='*60}")
    print(f"Pi IP (bat0): {PI_IP}")
    print(f"Drone Number: {DRONE_NUMBER} (auto-detected from IP)")
    print(f"Listen on: {LISTEN_IP}:{LISTEN_PORT}")
    print(f"Video Port (to PC): {VIDEO_PORT}")
    print(f"Tello: {TELLO_IP}:{TELLO_PORT} via {TELLO_DEV}")
    print(f"{'='*60}\n")
    # ------------------

    # Create sockets using original functions
    s_pc = create_pc_socket()
    s_tello = create_tello_socket()
    
    # Start video forwarding thread
    video_thread = threading.Thread(target=forward_video, daemon=True)
    video_thread.start()
    
    print("Waiting for commands from PC...")
    print("Video forwarding active - waiting for streamon command...\n")
    
    try:
        # Main forwarding loop
        forward_loop(s_pc, s_tello)
    
    except KeyboardInterrupt:
        print("\nShutting down...")
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        s_pc.close()
        s_tello.close()
        print("Sockets closed")

if __name__ == "__main__":
    main()
