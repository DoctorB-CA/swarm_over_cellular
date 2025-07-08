#!/bin/bash
echo "=== Drone Relay Status ==="
sudo systemctl status drone-relay.service

echo ""
echo "=== Recent Logs ==="
sudo journalctl -u drone-relay.service -n 20 --no-pager

echo ""
echo "=== Network Status ==="
echo "Listening ports:"
sudo netstat -ulnp | grep python

echo ""
echo "=== System Resources ==="
top -bn1 | head -5
