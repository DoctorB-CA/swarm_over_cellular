#!/usr/bin/env python3
"""
PC Controller for Tello Drone - DIRECT CONNECTION (No Pi)
Keyboard control with WASD and video streaming
For testing video streaming with drone directly connected to PC
"""

import socket
import time
import threading
import sys
import subprocess
import cv2
import numpy as np
from drone_translator import DroneTranslator
from pynput import keyboard

# Configuration - DIRECT TELLO CONNECTION
TELLO_IP = "192.168.10.1"  # Tello drone IP (standard)
TELLO_PORT = 8889  # Tello command port (standard)
PC_IP = "0.0.0.0"  # Bind to all interfaces
PC_PORT = 9000  # Port where PC receives responses (can be any unused port)
VIDEO_PORT = 11111  # Tello video stream port (standard)

DRONE_TYPE = "tello"

# Global variables
sock = None
tello_address = (TELLO_IP, TELLO_PORT)
translator = None
is_flying = False
running = True
video_enabled = False
video_capture = None  # Single video capture object
video_thread = None

# Continuous control variables
max_speed = 50  # Current max speed (set by 1-5 keys)
current_velocities = {'lr': 0, 'fb': 0, 'ud': 0, 'yaw': 0}  # Current velocities
target_velocities = {'lr': 0, 'fb': 0, 'ud': 0, 'yaw': 0}  # Target velocities based on keys held
keys_pressed = set()  # Currently pressed keys
ACCELERATION = 10  # Acceleration per update cycle
RC_UPDATE_RATE = 20  # Hz - how often to send RC commands

#-------------------------------

# Toggle video stream on/off
def toggle_video():
    """Toggle video stream on/off"""
    global video_enabled, video_capture, video_thread
    
    if video_enabled:
        # Turn off video
        print("\n[VIDEO] Turning OFF video stream")
        video_enabled = False
        
        # Stop video capture
        if video_capture is not None:
            temp_cap = video_capture
            video_capture = None  # Signal thread to exit
            time.sleep(0.2)  # Give thread time to exit
            temp_cap.release()
            cv2.destroyWindow("Tello Video")
        
        # Send streamoff command
        send_command('streamoff', wait_response=False)
        print("[VIDEO] Video stream stopped\n")
    else:
        # Turn on video
        print("\n[VIDEO] Turning ON video stream")
        print("[VIDEO] Sending 'streamon' command...")
        send_command('streamon', wait_response=False)
        print("[VIDEO] Waiting 2 seconds for stream to start...")
        time.sleep(2)
        
        # Start video capture in background
        print(f"[VIDEO] Starting capture on port {VIDEO_PORT}...")
        video_enabled = True
        start_video_capture()
        print("[VIDEO] Video stream started\n")

def send_command(command, wait_response=True):
    """Send a command to the Tello drone"""
    global sock, tello_address
    
    try:
        sock.sendto(command.encode('utf-8'), tello_address)
        #print(f"[CMD] '{command}' -> {TELLO_IP}")
    except Exception as e:
        print(f"[ERROR] Failed to send command: {e}")



# Removed keep_alive thread - not needed for direct connection

# ----- thread of receiving message from drone --------
def receive_responses():
    """Thread to continuously receive responses from drone"""
    global sock, running
    
    while running:
        try:
            sock.settimeout(1)
            response, addr = sock.recvfrom(1024)
            
            # Try to decode as UTF-8, skip if it's binary state data
            try:
                response = response.decode('utf-8')
                print(f"[RESP] {response}")
            except UnicodeDecodeError:
                # This is binary state data, skip it
                continue
            
        except socket.timeout:
            continue
        except Exception as e:
            if running:
                print(f"[ERROR] Receiving: {e}")

# ----- Continuous control functions -----
def update_target_velocities():
    """Update target velocities based on keys currently pressed"""
    global target_velocities, max_speed, keys_pressed
    
    # Reset targets
    target_velocities = {'lr': 0, 'fb': 0, 'ud': 0, 'yaw': 0}
    
    # Forward/Backward (W/S)
    if 'w' in keys_pressed:
        target_velocities['fb'] = max_speed
    if 's' in keys_pressed:
        target_velocities['fb'] = -max_speed
    
    # Left/Right (A/D)
    if 'a' in keys_pressed:
        target_velocities['lr'] = -max_speed
    if 'd' in keys_pressed:
        target_velocities['lr'] = max_speed
    
    # Up/Down (I/K)
    if 'i' in keys_pressed:
        target_velocities['ud'] = max_speed
    if 'k' in keys_pressed:
        target_velocities['ud'] = -max_speed
    
    # Yaw/Rotation (J/;)
    if 'j' in keys_pressed:
        target_velocities['yaw'] = -max_speed
    if ';' in keys_pressed:
        target_velocities['yaw'] = max_speed

def accelerate_towards_target(current, target, accel):
    """Smoothly accelerate current velocity towards target"""
    if current < target:
        return min(current + accel, target)
    elif current > target:
        return max(current - accel, target)
    return current

def rc_control_loop():
    """Continuous loop sending RC commands with acceleration"""
    global running, current_velocities, target_velocities, is_flying
    
    print("[RC] Continuous control loop started")
    
    last_sent_velocities = {'lr': 0, 'fb': 0, 'ud': 0, 'yaw': 0}
    
    while running:
        if is_flying:
            # Update current velocities towards targets with acceleration
            current_velocities['lr'] = accelerate_towards_target(
                current_velocities['lr'], target_velocities['lr'], ACCELERATION)
            current_velocities['fb'] = accelerate_towards_target(
                current_velocities['fb'], target_velocities['fb'], ACCELERATION)
            current_velocities['ud'] = accelerate_towards_target(
                current_velocities['ud'], target_velocities['ud'], ACCELERATION)
            current_velocities['yaw'] = accelerate_towards_target(
                current_velocities['yaw'], target_velocities['yaw'], ACCELERATION)
            
            # Only send if velocities changed (avoid spamming "rc 0 0 0 0")
            if current_velocities != last_sent_velocities:
                # Build RC command: rc left/right forward/back up/down yaw
                rc_cmd = f"rc {int(current_velocities['lr'])} {int(current_velocities['fb'])} {int(current_velocities['ud'])} {int(current_velocities['yaw'])}"
                
                # Send RC command
                send_command(rc_cmd, wait_response=False)
                last_sent_velocities = current_velocities.copy()
        
        time.sleep(1.0 / RC_UPDATE_RATE)  # 20 Hz update rate
    
    print("[RC] Continuous control loop stopped")

# Removed dynamic SDP file - not needed

#---- Video capture and display functions ------
def start_video_capture():
    """Start OpenCV video capture (non-blocking)"""
    global video_capture, video_thread
    
    print(f"[VIDEO] Starting capture on port {VIDEO_PORT}")
    
    # Start video capture in separate thread to not block commands
    thread = threading.Thread(target=_open_video_stream, daemon=True)
    thread.start()
    video_thread = thread

def _open_video_stream():
    """Open video stream in background thread (fully async)"""
    global video_capture
    
    # UDP stream with LARGER buffer for cellular networks (reduce packet loss impact)
    # fifo_size increased to 500KB, added buffer_size and reorder for jitter tolerance
    # flags=low_delay reduces buffering, err_detect=ignore_err tolerates corrupt frames
    stream_url = f"udp://0.0.0.0:{VIDEO_PORT}?overrun_nonfatal=1&fifo_size=500000&buffer_size=655360&reorder_queue_size=500"
    print(f"[VIDEO] Opening stream: {stream_url}")
    
    # Set environment variable to make FFmpeg more tolerant of errors
    import os
    os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'flags;low_delay|err_detect;ignore_err|skip_frame;0'
    
    # Open with FFmpeg - this will wait for first frame
    cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
    
    # Set flags to help with packet loss on cellular
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)  # Increased buffer for cellular jitter
    # Tell decoder to be aggressive about decoding even incomplete frames
    cap.set(cv2.CAP_PROP_FORMAT, -1)  # Accept any format
    
    # Give it time to receive first keyframe (up to 20 seconds for cellular)
    print(f"[VIDEO] Waiting for video stream (cellular networks may take longer)...")
    for attempt in range(40):  # Extended timeout for cellular
        if cap.isOpened() and cap.grab():
            print(f"[VIDEO] ✓ First frame received after {attempt * 0.5:.1f}s!")
            break
        time.sleep(0.5)
    else:
        print(f"[VIDEO ERROR] No video received on port {VIDEO_PORT} after 20 seconds")
        print(f"[VIDEO ERROR] Cellular network may have too much packet loss")
        return
    
    video_capture = cap
    
    # Start display thread
    display_thread = threading.Thread(target=display_drone_video, daemon=True)
    display_thread.start()

def display_drone_video():
    """Display video using OpenCV"""
    global video_capture, running, video_enabled
    
    window_name = "Tello Video"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 640, 480)
    
    print(f"[VIDEO] Display thread started")
    
    frame_count = 0
    valid_frames = 0
    last_frame_time = time.time()
    
    # Skip initial frames until we get a valid keyframe
    # On cellular: accept PARTIAL frames too (better than nothing)
    print(f"[VIDEO] Waiting for usable frame (accepting partial frames on cellular)...")
    keyframe_attempts = 0
    got_something = False
    for _ in range(100):  # Try more frames on cellular (more packet loss)
        if video_capture is None:
            return
        ret, frame = video_capture.read()
        keyframe_attempts += 1
        
        # Accept ANY frame with some data (even if partially corrupt)
        if ret and frame is not None:
            if frame.size > 0:
                print(f"[VIDEO] ✓ Got usable frame after {keyframe_attempts} attempts")
                got_something = True
                break
            # Even if frame.size == 0, keep trying - might just be a placeholder
        
        time.sleep(0.05)  # Shorter wait between attempts
    
    if not got_something:
        print(f"[VIDEO ERROR] No usable frames after 100 attempts")
        print(f"[VIDEO ERROR] Cellular packet loss may be too high (>10%) or stream not started")
        return
    
    while running and video_enabled and video_capture is not None:
        ret, frame = video_capture.read()
        
        # On cellular: display even partially corrupt frames (better than black screen)
        if ret and frame is not None:
            # Check if frame has any data at all
            if frame.size > 0:
                frame_count += 1
                valid_frames += 1
                
                # Add info overlay
                cv2.putText(frame, "Tello Drone", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                # Show FPS every second
                current_time = time.time()
                if current_time - last_frame_time >= 1.0:
                    fps = valid_frames / (current_time - last_frame_time)
                    valid_frames = 0
                    last_frame_time = current_time
                
                # Display frame (even if partially corrupt - cellular tolerance)
                try:
                    cv2.imshow(window_name, frame)
                except Exception as e:
                    # Frame might be corrupt, skip it
                    pass
                
                # Process OpenCV events (required for display)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        
        # Don't wait too long between frame attempts (keep reading to clear buffer)
        time.sleep(0.001)
    
    # Cleanup
    print(f"[VIDEO] Display thread stopped")
    cv2.destroyWindow(window_name)

def display_video():
    """Video manager thread (simplified for single drone)"""
    global running
    
    print("[VIDEO] Video manager thread started")
    
    while running:
        time.sleep(0.5)
    
    # Cleanup on shutdown
    print("[VIDEO] Shutting down video...")
    if video_capture is not None:
        video_capture.release()
        cv2.destroyAllWindows()
    
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
            print("\n[TAKEOFF] Drone is taking off... Please wait...")
            time.sleep(2)  # Wait 2 seconds after takeoff
            print("[TAKEOFF] Ready for next command\n")
        elif key_command == 'land' or key_command == 'emergency':
            is_flying = False
    else:
        print(f"[WARN] Unknown command: {key_command}")

# mega print:
def print_controls():
    """Print keyboard controls"""
    print("\n" + "="*60)
    print("TELLO DRONE KEYBOARD CONTROLS - DIRECT CONNECTION")
    print("="*60)
    print("Video Control:")
    print("  V - Toggle video stream ON/OFF")
    if video_enabled:
        print("  [ACTIVE] Video stream is ON")
    else:
        print("  [INACTIVE] Video stream is OFF")
    print("")
    print("Flight Control:")
    print("  T - Takeoff")
    print("  L - Land")
    print("")
    print("Movement (CONTINUOUS - Hold keys):")
    print("  W - Forward        S - Backward")
    print("  A - Left           D - Right")
    print("  I - Up             K - Down")
    print("  J - Rotate Left    ; - Rotate Right")
    print("  [INFO] Hold keys for smooth acceleration, release to decelerate")
    print("")
    print("Speed Control:")
    print("  1-5 - Set MAX speed (1=20, 2=35, 3=50, 4=70, 5=100)")
    print(f"  [CURRENT MAX SPEED: {max_speed}]")
    print("")
    print("Info:")
    print("  B - Battery level")
    print("  H - Height")
    print("")
    print("  ESC - Quit (lands drone first)")
    print("="*60)
    print(f"Drone Type: {DRONE_TYPE}")
    print(f"Tello IP: {TELLO_IP}:{TELLO_PORT}")
    print(f"Video Port: {VIDEO_PORT}")
    print(f"Current Speed: {translator.get_speed()}")
    print("="*60 + "\n")


# ---- Keyboard control with pynput ------
def on_press(key):
    """Handle key press events"""
    global keys_pressed, max_speed, running, is_flying
    
    try:
        # Get the character
        k = key.char
        
        # Movement keys - add to pressed set
        if k in ['w', 's', 'a', 'd', 'i', 'k', 'j', ';']:
            keys_pressed.add(k)
            update_target_velocities()
        
        # Speed control 1-5
        elif k == '1':
            max_speed = 20
            print(f"\n[SPEED] Max speed set to: {max_speed}\n")
        elif k == '2':
            max_speed = 35
            print(f"\n[SPEED] Max speed set to: {max_speed}\n")
        elif k == '3':
            max_speed = 50
            print(f"\n[SPEED] Max speed set to: {max_speed}\n")
        elif k == '4':
            max_speed = 70
            print(f"\n[SPEED] Max speed set to: {max_speed}\n")
        elif k == '5':
            max_speed = 100
            print(f"\n[SPEED] Max speed set to: {max_speed}\n")
        
        # Takeoff
        elif k == 't':
            print("\n[TAKEOFF] Sending takeoff command...")
            send_command('takeoff', wait_response=False)
            is_flying = True
            time.sleep(2)
            print("[TAKEOFF] Ready for flight!\n")
        
        # Land
        elif k == 'l':
            print("\n[LAND] Landing drone...")
            send_command('land', wait_response=False)
            is_flying = False
            # Reset all velocities
            keys_pressed.clear()
            update_target_velocities()
        
        # Video toggle
        elif k == 'v':
            toggle_video()
        
        # Info commands
        elif k == 'b':
            send_command('battery?', wait_response=False)
        elif k == 'h':
            send_command('height?', wait_response=False)
        
        # Help
        elif k == '?':
            print_controls()
    
    except AttributeError:
        # Special keys (arrows, etc) - ignore
        pass

def on_release(key):
    """Handle key release events"""
    global keys_pressed, running
    
    try:
        k = key.char
        
        # Remove from pressed set and update velocities
        if k in keys_pressed:
            keys_pressed.remove(k)
            update_target_velocities()
    
    except AttributeError:
        pass
    
    # Check for Esc key to quit
    if key == keyboard.Key.esc:
        print("\n[INFO] ESC pressed - shutting down...")
        global is_flying
        if is_flying:
            print("[INFO] Landing drone first...")
            send_command('land', wait_response=True)
            time.sleep(3)
        return False  # Stop listener

def keyboard_control():
    """Start keyboard listener"""
    global running
    
    print("\n" + "="*60)
    print("CONTINUOUS CONTROL MODE ACTIVE - DIRECT CONNECTION")
    print("="*60)
    print("Hold W/S/A/D/I/K/J/; for smooth movement")
    print("Press 'V' to toggle video, '?' for full controls, ESC to quit")
    print("="*60 + "\n")
    
    # Start keyboard listener
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()
    
    running = False

# ---- the main thread -----------
def main():
    global sock, tello_address, translator, running
        
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((PC_IP, PC_PORT))
    
    translator = DroneTranslator(drone_type=DRONE_TYPE)
    
    # -- printing stuff --
    print(f"\n{'='*60}")
    print(f"TELLO DRONE KEYBOARD CONTROLLER - DIRECT CONNECTION")
    print(f"{'='*60}")
    print(f"PC: Listening on port {PC_PORT}")
    print(f"Tello: {TELLO_IP}:{TELLO_PORT}")
    print(f"Video: Port {VIDEO_PORT}")
    print(f"Drone Type: {DRONE_TYPE}")
    print(f"{'='*60}\n")
    # --------------------------
    
    response_thread = threading.Thread(target=receive_responses, daemon=True)
    response_thread.start()
    
    video_thread = threading.Thread(target=display_video, daemon=True)
    video_thread.start()
    
    rc_thread = threading.Thread(target=rc_control_loop, daemon=True)
    rc_thread.start()
    
    try:
        # -- printing staff --
        print("[INIT] Initializing Tello...")
        print(f"[INIT] Sending 'command' to {TELLO_IP}")
        sock.sendto("command".encode('utf-8'), tello_address)
        
        time.sleep(2)
        print("[INIT] Tello ready!")
        
        print(f"[INIT] Checking battery...")
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
