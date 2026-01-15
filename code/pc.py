#!/usr/bin/env python3
"""
PC Controller for Tello Drone via Raspberry Pi
Keyboard control with WASD and video streaming
"""

import socket
import time
import threading
import sys
import subprocess
from drone_translator import DroneTranslator

# Configuration
PI_IPS = [
    "10.0.0.1",  # Drone 1
    "10.0.0.2"   # Drone 2
]
PI_PORT = 20002  # Port where Pi listens for PC commands (MUST match pi.py LISTEN_PORT)
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
video_group = set()  # Set of drone indices to show video from
video_enabled = False  # Whether video display is enabled
ffplay_processes = {}  # Dict of drone_idx -> video thread

#-------------------------------

# in and out of the VIDEO SCREEN BY PRESSING v
def toggle_video():
    """Toggle current drone in/out of video group"""
    global video_group, video_enabled
    
    if current_drone_index in video_group:
        video_group.remove(current_drone_index)
        print(f"\n[VIDEO] Drone {current_drone_index + 1} REMOVED from video group")
    else:
        video_group.add(current_drone_index)
        print(f"\n[VIDEO] Drone {current_drone_index + 1} ADDED to video group")
        video_enabled = True
    
    if len(video_group) > 0:
        print(f"[VIDEO] Showing video from {len(video_group)} drone(s): {sorted([i+1 for i in video_group])}")
    else:
        print(f"[VIDEO] No drones in video group")
        video_enabled = False
    print()

# in and out of the multicast BY PRESSING M "in and out, 15 minutes adventure"
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

# move to the next drone if press "next"
def switch_drone(direction):
    """Switch to next or previous drone"""
    global current_drone_index, pi_address
    
    if direction == 'next':
        current_drone_index = (current_drone_index + 1) % len(PI_IPS) #cyclic
    elif direction == 'prev':
        current_drone_index = (current_drone_index - 1) % len(PI_IPS) #cyclic
    
    pi_address = (PI_IPS[current_drone_index], PI_PORT)
    print(f"\n{'='*60}")
    print(f"[SWITCH] Now controlling Drone {current_drone_index + 1}")
    print(f"[SWITCH] IP: {PI_IPS[current_drone_index]}:{PI_PORT}")
    in_multicast = " (IN MULTICAST)" if current_drone_index in multicast_group else ""
    print(f"[SWITCH] Status{in_multicast}")
    print(f"{'='*60}\n")


# send the commend to drone
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
        print(f"[C-ID:{command_id}] [MULTICAST] '{command}' -> {len(multicast_group)} drones")
        for drone_idx in multicast_group:
            target_address = (PI_IPS[drone_idx], PI_PORT)
            sock.sendto(command.encode('utf-8'), target_address)
    else:
        # Send to current drone only
        print(f"[C-ID:{command_id}] [DRONE {current_drone_index + 1}] '{command}'") 
        sock.sendto(command.encode('utf-8'), pi_address)



# keep alive 
def send_keep_alive():
    pass


# ----- tread of reciving message from drone --------
def receive_responses():
    """Thread to continuously receive responses from drone"""
    global sock, running
    
    while running:
        try:
            sock.settimeout(1)
            response, _ = sock.recvfrom(1024)
            response = response.decode('utf-8')
            print(f"[RESP] {response}")
        except socket.timeout:
            continue
        except Exception as e:
            if running:
                print(f"[ERROR] Receiving: {e}")

# dynamic sdp file
def create_sdp_file(drone_idx, video_port):
    """Create SDP file for Tello video stream from template"""
    import os
    
    # Try to read template, fallback to inline if not found
    template_path = os.path.join(os.path.dirname(__file__), 'tello_template.sdp')
    
    try:
        with open(template_path, 'r') as f:
            sdp_content = f.read()
        # Replace placeholders
        sdp_content = sdp_content.replace('{DRONE_NUM}', str(drone_idx + 1))
        sdp_content = sdp_content.replace('{VIDEO_PORT}', str(video_port))
    except FileNotFoundError:
        # Fallback to inline SDP
        sdp_content = f"""v=0
o=- 0 0 IN IP4 {PC_IP}
s=Tello Drone {drone_idx + 1}
c=IN IP4 {PC_IP}
t=0 0
a=tool:libavformat
m=video {video_port} RTP/AVP 96
b=AS:200
a=rtpmap:96 H264/90000
a=fmtp:96 packetization-mode=1
"""
    
    sdp_filename = f"/tmp/tello_drone_{drone_idx + 1}.sdp"
    with open(sdp_filename, 'w') as f:
        f.write(sdp_content)
    
    return sdp_filename

#---- tread of viedo, usless fo now ------
def display_video():
    """Thread to manage video - currently just placeholder"""
    global running, video_enabled
    
    print("[VIDEO] Video manager thread started (no display)")
    
    while running:
        time.sleep(1)
    
    print("[VIDEO] Video manager thread closed")
# -----------------------

# transtale + chekcing if flying
def process_key(key_command):
    """Process a key command and send to drone"""
    global translator, is_flying
    
    drone_cmd = translator.translate(key_command) 
    
    if drone_cmd:
        send_command(drone_cmd, wait_response=False)
        
        if key_command == 'takeoff':
            is_flying = True
        elif key_command == 'land' or key_command == 'emergency':
            is_flying = False
    else:
        print(f"[WARN] Unknown command: {key_command}")

# mega print:
def print_controls():
    """Print keyboard control
                print(f"[TELLO -> PI] Received: {response}")s"""
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
        print(f"  [INFO] Commands go to current drone only")
    print("")
    print("Video Control:")
    print("  V - Add current drone to video display")
    print("  X - Remove current drone from video display")
    if len(video_group) > 0:
        print(f"  [ACTIVE] Showing video from: {sorted([i+1 for i in video_group])}")
        print(f"  [LAYOUT] Large=Drone {current_drone_index + 1}, Small=Others")
    else:
        print("  [INACTIVE] No video streams active")
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


# ---- tread of controling ------
def keyboard_control():
    """Main keyboard control loop"""
    global running, is_flying
    
    print("Enter commands (type 'help' for controls):")
    
    cmd_map = {
        't': 'takeoff',
        'l': 'land',
        'e': 'emergency',
        'w': 'forward',
        's': 'backward',
        'a': 'left',
        'd': 'right',
        'i': 'up',
        'k': 'down',
        'j': 'rotate_left',
        ';': 'rotate_right',
        '1': 'set_speed_20',
        '2': 'set_speed_35',
        '3': 'set_speed_50',
        '4': 'set_speed_70',
        '5': 'set_speed_100',
        'b': 'battery',
        'h': 'height',
        'q': 'quit',
    }
    
    while running:
        try:
            user_input = input("> ").strip().lower()
            
            if not user_input:
                continue
            
            elif user_input == 'help':
                print_controls()
                continue
            
            elif user_input == 'n':
                switch_drone('next')
                continue
            
            elif user_input == 'p':
                switch_drone('prev')
                continue
            
            elif user_input == 'm':
                toggle_multicast()    
                continue
            
            elif user_input == 'v':
                toggle_video()
                if len(video_group) == 1:
                    print("[VIDEO] Sending 'streamon' command...")
                    process_key('streamon')
                continue
            
            elif user_input == 'x':   #what is this?
                was_last = len(video_group) == 1 and current_drone_index in video_group
                toggle_video()
                if was_last and len(video_group) == 0:
                    print("[VIDEO] Sending 'streamoff' command...")
                    send_command('streamoff', wait_response=False)
                continue
            
            elif user_input == 'q' or user_input == 'quit':
                print("\n[INFO] Shutting down...")
                if is_flying:
                    print("[INFO] Landing drone first...")
                    send_command('land', wait_response=True)
                    time.sleep(3)
                running = False
                break
            
            elif user_input in cmd_map:  # normal keys
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
# ----------------------

# ---- the main thread -----------
def main():
    global sock, pi_address, translator, running
        
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # creating soket IP4 AND UDP
    sock.bind((PC_IP, PC_PORT))
    
    pi_address = (PI_IPS[current_drone_index], PI_PORT)
    translator = DroneTranslator(drone_type=DRONE_TYPE)
    # -- printing  staf --
    print(f"\n{'='*60}")
    print(f"TELLO DRONE KEYBOARD CONTROLLER")
    print(f"{'='*60}")
    print(f"PC: {PC_IP}:{PC_PORT}")
    print(f"Available Drones: {len(PI_IPS)}")
    for i, ip in enumerate(PI_IPS): # index + item in list
        active = " <- ACTIVE" if i == current_drone_index else ""
        in_group = " [M]" if i in multicast_group else ""
        print(f"  Drone {i+1}: {ip}:{PI_PORT}{active}{in_group}")
    print(f"Drone Type: {DRONE_TYPE}")
    if len(multicast_group) > 0:
        print(f"Multicast: ACTIVE - {len(multicast_group)} drone(s) in group")
    else:
        print(f"Multicast: INACTIVE")
    print(f"{'='*60}\n")
    # --------------------------
    
    response_thread = threading.Thread(target=receive_responses, daemon=True)
    response_thread.start()
    
    video_thread = threading.Thread(target=display_video, daemon=True)
    video_thread.start()
    
    try:
        # -- printing staff --
        print("[INIT] Initializing all drones...")
        for i, ip in enumerate(PI_IPS):
            target_address = (ip, PI_PORT)
            print(f"[INIT] Sending 'command' to Drone {i+1} ({ip})")
            sock.sendto("command".encode('utf-8'), target_address)
        
        time.sleep(2)
        print("[INIT] All drones ready!")
        
        print(f"[INIT] Checking battery of Drone {current_drone_index + 1}...")
        send_command("battery?", wait_response=False)
        time.sleep(1)
        
        print_controls()
        # -----------------

        # inputing threads: (keyboard thread is == main thread ?)
        keyboard_control()
    
    except Exception as e:
        print(f"[ERROR] {e}")
        running = False
    
    finally:
        if is_flying:
            print("\n[SHUTDOWN] Landing drone...")
            send_command('land', wait_response=True)
            time.sleep(3)
        
        print("[SHUTDOWN] Closing...")
        sock.close()
# -------------------------------
if __name__ == "__main__":
    main()
