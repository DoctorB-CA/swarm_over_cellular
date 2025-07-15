#!/usr/bin/env python3
"""
Simple UDP packet reception test to debug WSL networking issues.
"""

import socket
import time
import sys

def test_udp_reception(port=5000, timeout=10):
    """Test if we can receive UDP packets on the specified port"""
    
    print(f"Testing UDP reception on port {port} for {timeout} seconds...")
    
    try:
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", port))
        sock.settimeout(1.0)  # 1 second timeout for recv
        
        print(f"Socket bound to 0.0.0.0:{port}")
        print("Waiting for packets...")
        
        start_time = time.time()
        packet_count = 0
        
        while time.time() - start_time < timeout:
            try:
                data, addr = sock.recvfrom(1500)
                packet_count += 1
                
                print(f"Packet {packet_count}: {len(data)} bytes from {addr}")
                print(f"  First 50 bytes (hex): {data[:50].hex()}")
                
                # Check for common video formats
                if data.startswith(b'\x00\x00\x00\x01'):
                    print("  -> H.264 NAL unit detected")
                elif data.startswith(b'G'):
                    print("  -> Possible MPEG-TS")
                elif b'RTP' in data[:20]:
                    print("  -> Possible RTP packet")
                else:
                    print(f"  -> Unknown format, first 4 bytes: {data[:4].hex()}")
                    
                if packet_count >= 10:  # Stop after 10 packets
                    print("Received enough packets, stopping...")
                    break
                    
            except socket.timeout:
                # No packet received in 1 second, continue waiting
                continue
                
        sock.close()
        
        print(f"\nTest completed: Received {packet_count} packets in {time.time() - start_time:.1f} seconds")
        
        if packet_count == 0:
            print("❌ No packets received - possible network issue")
            return False
        else:
            print("✅ Packets are being received")
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    test_udp_reception(port)
