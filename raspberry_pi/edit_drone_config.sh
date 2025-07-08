#!/bin/bash
echo "Opening drone relay configuration..."
echo "Remember to restart the service after making changes!"
sudo nano /opt/drone_relay/relay_config.py
echo ""
echo "Restart service with: sudo systemctl restart drone-relay.service"
