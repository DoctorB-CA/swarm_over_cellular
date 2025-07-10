#!/usr/bin/env python3
import socket
import time
import sys

# Simple script to control a Tello drone via UDP sockets
# Ensure your Raspberry Pi is using Python 3 and is connected to the drone's Wi-Fi network

def send_command(command: str, sock: socket.socket, address: tuple):
    """
    Send a command to the drone, safely decode its response, and print it.
    """
    sock.sendto(command.encode('utf-8'), address)
    try:
        response, _ = sock.recvfrom(1024)
        try:
            text = response.decode('utf-8')
        except UnicodeDecodeError:
            # Fallback: show raw bytes and attempt latin-1 decode
            print(f"[Warning] UTF-8 decode failed, raw bytes: {response}")
            text = response.decode('latin-1', errors='replace')
        print(f"Drone response: {text}")
    except socket.timeout:
        print("No response received (timeout).")

if __name__ == '__main__':
    # Run with Python 3: python3 script.py
    # Drone network settings
    DRONE_ADDRESS = ('192.168.10.1', 8889)
    LOCAL_ADDRESS = ('', 9000)  # Bind to any available interface on port 9000

    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(LOCAL_ADDRESS)
    sock.settimeout(5)

    # Enter SDK mode
    send_command('command', sock, DRONE_ADDRESS)
    time.sleep(1)

    # Takeoff
    send_command('takeoff', sock, DRONE_ADDRESS)
    time.sleep(5)

    # Land
    send_command('land', sock, DRONE_ADDRESS)

    # Close socket
    sock.close()
