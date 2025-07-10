#!/usr/bin/env python3
import socket
import time
from djitellopy import Tello

LISTEN_PORT = 5005
BUF_SIZE    = 1024
MOVE_DIST   = 20    # cm per command

def main():
    # --- set up drone ---
    drone = Tello()
    drone.connect()
    print(f"[DRONE] Battery: {drone.get_battery()}%")

    # --- set up UDP socket ---
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', LISTEN_PORT))
    print(f"[PI] Listening on UDP port {LISTEN_PORT}...")

    try:
        while True:
            data, addr = sock.recvfrom(BUF_SIZE)
            if not data:
                continue
            cmd = data.decode().strip().lower()

            print(f"[PI] Received '{cmd}' from {addr}")
            if cmd == 't':
                print("→ Takeoff")
                drone.takeoff()
            elif cmd == 'l':
                print("→ Land")
                drone.land()
            elif cmd == 'w':
                print(f"→ Forward {MOVE_DIST}cm")
                drone.move_forward(MOVE_DIST)
            elif cmd == 's':
                print(f"→ Back {MOVE_DIST}cm")
                drone.move_back(MOVE_DIST)
            elif cmd == 'a':
                print(f"→ Left {MOVE_DIST}cm")
                drone.move_left(MOVE_DIST)
            elif cmd == 'd':
                print(f"→ Right {MOVE_DIST}cm")
                drone.move_right(MOVE_DIST)
            else:
                print(f"Ignoring unknown command '{cmd}'")
            # slight delay so commands don't stack too fast
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nShutting down…")
    finally:
        sock.close()
        drone.end()
        print("[DRONE] Connection closed.")

if __name__ == "__main__":
    main()
