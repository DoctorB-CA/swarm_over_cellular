#!/usr/bin/env python3
"""
PC Test Script - WiFi Hotspot (No Cellular/Wireguard)
Receives RTP video from Pi over WiFi and displays
"""

import cv2
import os
import time

# Configuration
VIDEO_PORT = 11111

def main():
    print(f"\n{'='*60}")
    print(f"PC TEST - WIFI HOTSPOT MODE")
    print(f"{'='*60}")
    print(f"Listening on port: {VIDEO_PORT}")
    print(f"Expecting H.264 UDP stream from Pi")
    print(f"{'='*60}\n")
    
    # Open video capture via UDP
    stream_url = f"udp://0.0.0.0:{VIDEO_PORT}?overrun_nonfatal=1&fifo_size=500000&buffer_size=655360"
    print(f"[VIDEO] Opening stream: {stream_url}")
    cap = cv2.VideoCapture(stream_url)
    
    print(f"[VIDEO] Opened: {cap.isOpened()}")
    if cap.isOpened():
        print(f"[VIDEO] Backend: {cap.getBackendName()}")
    
    if not cap.isOpened():
        print("[ERROR] Failed to open video stream!")
        print("[ERROR] Check if Pi is running and sending video to this IP")
        print("[ERROR] PC IP should be: 10.160.77.127")
        return
    
    print("\n[READY] Waiting for video frames... Press 'q' to quit.\n")
    
    frame_count = 0
    start_time = time.time()
    
    while True:
        ret, frame = cap.read()
        
        if ret and frame is not None and frame.size > 0:
            frame_count += 1
            
            # Show frame info periodically
            if frame_count % 30 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed if elapsed > 0 else 0
                print(f"[VIDEO] Frame {frame_count} | FPS: {fps:.1f} | Shape: {frame.shape}")
            
            # Display frame
            cv2.imshow('Tello Video - WiFi Test', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\n[QUIT] User pressed 'q'")
                break
        else:
            print(f"[DEBUG] Waiting for frame... (ret={ret})")
            time.sleep(0.1)
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    print("[SHUTDOWN] Done")

if __name__ == "__main__":
    main()
