#!/usr/bin/env python3
"""
Raspberry Pi Middleman for Tello Drone Control
Receives commands from PC and forwards to Tello drone
Receives responses from drone and forwards back to PC
"""

import socket
import threading
import time

# Configuration
PI_IP = "10.0.0.1"
PI_PORT = 9000  # Port to listen for PC commands

TELLO_IP = "192.168.10.1"  # Tello drone default IP
TELLO_PORT = 8889  # Tello command port

# Global variables
pc_address = None  # Will be set when we receive first message from PC
tello_sock = None
pc_sock = None

def receive_from_tello():
    """
    Thread to continuously receive responses from Tello and forward to PC
    """
    global pc_address, tello_sock
    
    print("Tello receiver thread started")
    
    while True:
        try:
            # Receive response from Tello
            response, _ = tello_sock.recvfrom(1024)
            response_str = response.decode('utf-8')
            print(f"[TELLO -> PI] Received: {response_str}")
            
            # Forward to PC if we know PC address
            if pc_address:
                pc_sock.sendto(response, pc_address)
                print(f"[PI -> PC] Forwarded to {pc_address}: {response_str}")
            
        except Exception as e:
            print(f"Error receiving from Tello: {e}")
            time.sleep(0.1)

def main():
    global pc_address, tello_sock, pc_sock
    
    # Create UDP socket for PC communication
    pc_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    pc_sock.bind((PI_IP, PI_PORT))
    
    # Create UDP socket for Tello communication
    tello_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    tello_sock.bind(('', 8889))  # Bind to port 8889 to receive from Tello
    
    print(f"Pi Middleman started on {PI_IP}:{PI_PORT}")
    print(f"Forwarding to Tello at {TELLO_IP}:{TELLO_PORT}")
    
    # Start thread to receive from Tello
    tello_thread = threading.Thread(target=receive_from_tello, daemon=True)
    tello_thread.start()
    
    print("Waiting for commands from PC...")
    
    try:
        while True:
            # Receive command from PC
            data, address = pc_sock.recvfrom(1024)
            command = data.decode('utf-8')
            
            # Store PC address for sending responses back
            if pc_address != address:
                pc_address = address
                print(f"PC connected from: {pc_address}")
            
            print(f"[PC -> PI] Received command: {command}")
            
            # Forward command to Tello
            tello_sock.sendto(data, (TELLO_IP, TELLO_PORT))
            print(f"[PI -> TELLO] Forwarded: {command}")
    
    except KeyboardInterrupt:
        print("\nShutting down...")
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        pc_sock.close()
        tello_sock.close()
        print("Sockets closed")

if __name__ == "__main__":
    main()