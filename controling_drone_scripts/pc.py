#!/usr/bin/env python3
"""
PC Controller for Tello Drone via Raspberry Pi
Keyboard control with WASD and more
"""

import socket
import time
import threading
import sys
from drone_translator import DroneTranslator

# Configuration
PI_IPS = [
   "10.0.0.1",  # Drone 1
    "10.0.0.2"  # Drone 2
]
PI_PORT = 9000  # Port where Pi listens for PC commands
PC_IP = "10.7.0.2"
PC_PORT = 9001  # Port where PC receives responses

DRONE_TYPE = "tello"

# Global variables
sock = None
pi_address = None
translator = None
is_flying = False
running = True
current_drone_index = 0  # Start with first drone
multicast_group = set()  # Set of drone indices in multicast group
multicast_mode = False  # Whether multicast mode is active
command_id = 0  # Incremental command ID

def toggle_multicast():
    """Toggle current drone in/out of multicast group"""
    global multicast_group, multicast_mode
    
    if current_drone_index in multicast_group:
        multicast_group.remove(current_drone_index)
        print(f"\n[MULTICAST] Drone {current_drone_index + 1} REMOVED from multicast group")
    else:
        multicast_group.add(current_drone_index)
        print(f"\n[MULTICAST] Drone {current_drone_index + 1} ADDED to multicast group")
    
    if len(multicast_group) > 0:
        print(f"[MULTICAST] Group now has {len(multicast_group)} drone(s): {sorted([i+1 for i in multicast_group])}")
        multicast_mode = True
    else:
        print(f"[MULTICAST] Group is empty, multicast mode disabled")
        multicast_mode = False
    print()

def switch_drone(direction):
    """Switch to next or previous drone"""
    global current_drone_index, pi_address
    
    if direction == 'next':
        current_drone_index = (current_drone_index + 1) % len(PI_IPS)
    elif direction == 'prev':
        current_drone_index = (current_drone_index - 1) % len(PI_IPS)
    
    pi_address = (PI_IPS[current_drone_index], PI_PORT)
    print(f"\n{'='*60}")
    print(f"[SWITCH] Now controlling Drone {current_drone_index + 1}")
    print(f"[SWITCH] IP: {PI_IPS[current_drone_index]}:{PI_PORT}")
    in_multicast = " (IN MULTICAST)" if current_drone_index in multicast_group else ""
    print(f"[SWITCH] Status{in_multicast}")
    print(f"{'='*60}\n")

def send_command(command, wait_response=True, use_multicast=True):
    """
    Send a command to the drone(s) via Pi
    If multicast group has drones and use_multicast=True, sends to all drones in group
    Otherwise sends to current drone only
    """
    global sock, pi_address, command_id
    
    command_id += 1
    
    if use_multicast and len(multicast_group) > 0:
        # Send to all drones in multicast group
        print(f"[C-ID:{command_id}] [MULTICAST] [CMD] {command} -> Drones {sorted([i+1 for i in multicast_group])}")
        for drone_idx in multicast_group:
            target_address = (PI_IPS[drone_idx], PI_PORT)
            sock.sendto(command.encode('utf-8'), target_address)
    else:
        # Send to current drone only
        print(f"[C-ID:{command_id}] [DRONE {current_drone_index + 1}] [CMD] {command}")
        sock.sendto(command.encode('utf-8'), pi_address)
    
    if wait_response:
        try:
            sock.settimeout(5)
            response, _ = sock.recvfrom(1024)
            response = response.decode('utf-8')
            print(f"[RESP] {response}")
            return response
        except socket.timeout:
            print(f"[RESP] Timeout")
            return None
    return None

def receive_responses():
    """Thread to continuously receive responses from drone"""
    global sock, running
    
    while running:
        try:
            sock.settimeout(1)
            response, _ = sock.recvfrom(1024)
            response = response.decode('utf-8')
            print(f"[DRONE {current_drone_index + 1}] [RESP] {response}")
        except socket.timeout:
            continue
        except Exception as e:
            if running:
                print(f"[ERROR] Receiving: {e}")

def process_key(key_command):
    """Process a key command and send to drone"""
    global translator, is_flying
    
    # Translate key to drone command
    drone_cmd = translator.translate(key_command)
    
    if drone_cmd:
        send_command(drone_cmd, wait_response=False)
        
        # Track flying state
        if key_command == 'takeoff':
            is_flying = True
        elif key_command == 'land' or key_command == 'emergency':
            is_flying = False
    else:
        print(f"[WARN] Unknown command: {key_command}")

def print_controls():
    """Print keyboard controls"""
    print("\n" + "="*60)
    print("KEYBOARD CONTROLS")
    print("="*60)
    print("Drone Switching:")
    print("  N - Next drone")
    print("  P - Previous drone")
    print("")
    print("Multicast Control:")
    print("  M - Add/Remove current drone to/from multicast group")
    if len(multicast_group) > 0:
        print(f"  [ACTIVE] Multicast Group: {sorted([i+1 for i in multicast_group])}")
        print(f"  [INFO] Commands will go to ALL drones in group")
    else:
        print("  [INACTIVE] No drones in multicast group")
        print("  [INFO] Commands go to current drone only")
    print("")
    print("Flight Control:")
    print("  T - Takeoff")
    print("  L - Land")
    print("  E - Emergency stop")
    print("")
    print("Movement:")
    print("  W - Forward        S - Backward")
    print("  A - Left           D - Right")
    print("  I - Up             K - Down")
    print("  J - Rotate Left    ; - Rotate Right")
    print("")
    print("Speed Control:")
    print("  1-5 - Set speed (1=slow, 5=fast)")
    print("")
    print("Info:")
    print("  B - Battery level")
    print("  H - Height")
    print("")
    print("  Q - Quit (lands all drones first)")
    print("="*60)
    print(f"Drone Type: {DRONE_TYPE}")
    print(f"Current Speed: {translator.get_speed()}")
    print(f"Available Drones: {len(PI_IPS)}")
    in_multicast = " [IN MULTICAST]" if current_drone_index in multicast_group else ""
    print(f"Currently Viewing: Drone {current_drone_index + 1} ({PI_IPS[current_drone_index]}){in_multicast}")
    if len(multicast_group) > 0:
        print(f"Command Target: ALL {len(multicast_group)} drone(s) in multicast group")
    else:
        print(f"Command Target: Current drone only")
    print("="*60 + "\n")

def keyboard_control():
    """Main keyboard control loop"""
    global running, is_flying
    
    print("Enter commands (type 'help' for controls):")
    
    # Command mapping from user input to key commands
    cmd_map = {
        # Flight control
        't': 'takeoff',
        'l': 'land',
        'e': 'emergency',
        
        # Movement
        'w': 'forward',
        's': 'backward',
        'a': 'left',
        'd': 'right',
        'i': 'up',
        'k': 'down',
        'j': 'rotate_left',
        ';': 'rotate_right',
        
        # Speed
        '1': 'set_speed_20',
        '2': 'set_speed_35',
        '3': 'set_speed_50',
        '4': 'set_speed_70',
        '5': 'set_speed_100',
        
        # Info
        'b': 'battery',
        'h': 'height',
        
        # Quit
        'q': 'quit',
    }
    
    while running:
        try:
            user_input = input("> ").strip().lower()
            
            if not user_input:
                continue
            
            if user_input == 'help':
                print_controls()
                continue
            
            # Drone switching
            if user_input == 'n':
                switch_drone('next')
                continue
            
            if user_input == 'p':
                switch_drone('prev')
                continue
            
            # Multicast toggle
            if user_input == 'm':
                toggle_multicast()
                continue
            
            if user_input == 'q' or user_input == 'quit':
                print("\n[INFO] Shutting down...")
                if is_flying:
                    print("[INFO] Landing drone first...")
                    send_command('land', wait_response=True)
                    time.sleep(3)
                running = False
                break
            
            # Process single character commands
            if user_input in cmd_map:
                key_cmd = cmd_map[user_input]
                process_key(key_cmd)
            else:
                print(f"[WARN] Unknown input: '{user_input}' (type 'help' for controls)")
        
        except KeyboardInterrupt:
            print("\n[INFO] Interrupted by user")
            running = False
            break
        except Exception as e:
            print(f"[ERROR] {e}")

def main():
    global sock, pi_address, translator, running
    
    # Initialize translator
    translator = DroneTranslator(drone_type=DRONE_TYPE)
    
    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((PC_IP, PC_PORT))
    
    pi_address = (PI_IPS[current_drone_index], PI_PORT)
    
    print(f"\n{'='*60}")
    print(f"TELLO DRONE KEYBOARD CONTROLLER")
    print(f"{'='*60}")
    print(f"PC: {PC_IP}:{PC_PORT}")
    print(f"Available Drones: {len(PI_IPS)}")
    for i, ip in enumerate(PI_IPS):
        active = " <- ACTIVE" if i == current_drone_index else ""
        in_group = " [M]" if i in multicast_group else ""
        print(f"  Drone {i+1}: {ip}:{PI_PORT}{active}{in_group}")
    print(f"Drone Type: {DRONE_TYPE}")
    if len(multicast_group) > 0:
        print(f"Multicast: ACTIVE - {len(multicast_group)} drone(s) in group")
    else:
        print(f"Multicast: INACTIVE")
    print(f"{'='*60}\n")
    
    # Start response receiver thread
    response_thread = threading.Thread(target=receive_responses, daemon=True)
    response_thread.start()
    
    try:
        # Initialize ALL drones
        print("[INIT] Initializing all drones...")
        for i, ip in enumerate(PI_IPS):
            target_address = (ip, PI_PORT)
            print(f"[INIT] Sending 'command' to Drone {i+1} ({ip})")
            sock.sendto("command".encode('utf-8'), target_address)
        
        time.sleep(2)  # Wait for all drones to initialize
        print("[INIT] All drones ready!")
        
        # Check battery of current drone
        print(f"[INIT] Checking battery of Drone {current_drone_index + 1}...")
        send_command("battery?", wait_response=False)
        time.sleep(1)
        
        # Show controls and start keyboard input
        print_controls()
        keyboard_control()
    
    except Exception as e:
        print(f"[ERROR] {e}")
        running = False
    
    finally:
        # Clean shutdown
        if is_flying:
            print("\n[SHUTDOWN] Landing drone...")
            send_command('land', wait_response=True)
            time.sleep(3)
        
        running = False
        sock.close()
        print("[SHUTDOWN] Connection closed")

if __name__ == "__main__":
    main()
