#!/usr/bin/env python3
"""
Test FFmpeg UDP reception directly to compare with Python socket reception
"""

import subprocess
import time
import threading

def test_ffmpeg_udp(port=5000, timeout=10):
    """Test if FFmpeg can receive UDP data on the specified port"""
    
    print(f"Testing FFmpeg UDP reception on port {port} for {timeout} seconds...")
    
    # FFmpeg command to just receive and dump UDP data (no processing)
    ffmpeg_cmd = [
        'ffmpeg',
        '-protocol_whitelist', 'file,udp',
        '-f', 'h264',
        '-i', f'udp://0.0.0.0:{port}?fifo_size=1000000&overrun_nonfatal=1',
        '-f', 'null',  # Discard output, just test reception
        '-loglevel', 'info',
        '-'
    ]
    
    print(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
    
    try:
        # Start FFmpeg with timeout
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print(f"FFmpeg process started (PID: {process.pid})")
        print("Waiting for UDP data...")
        
        # Wait for the specified timeout
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            print(f"FFmpeg completed normally")
            print(f"Return code: {process.returncode}")
        except subprocess.TimeoutExpired:
            print(f"FFmpeg running for {timeout} seconds (timeout as expected)")
            process.kill()
            stdout, stderr = process.communicate()
        
        print(f"\nFFmpeg stderr output:")
        print(stderr)
        
        # Analyze the output
        if "frame=" in stderr:
            print("✅ FFmpeg is receiving and processing frames")
            return True
        elif "Connection refused" in stderr or "No route to host" in stderr:
            print("❌ FFmpeg cannot connect to UDP port")
            return False
        elif "Invalid data found" in stderr:
            print("⚠️ FFmpeg is receiving data but cannot decode it")
            return True  # At least receiving data
        else:
            print("❓ FFmpeg started but unclear if data is being received")
            return False
            
    except Exception as e:
        print(f"❌ Error running FFmpeg: {e}")
        return False

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    test_ffmpeg_udp(port)
