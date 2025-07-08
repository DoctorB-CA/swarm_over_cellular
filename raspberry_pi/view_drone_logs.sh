#!/bin/bash
echo "=== Live Drone Relay Logs ==="
echo "Press Ctrl+C to exit"
sudo journalctl -u drone-relay.service -f
