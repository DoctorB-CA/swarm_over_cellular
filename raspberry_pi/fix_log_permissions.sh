#!/bin/bash
echo "Setting up drone relay log permissions..."

# Create log directory if it doesn't exist
sudo mkdir -p /var/log/drone_relay

# Create the log file if it doesn't exist
sudo touch /var/log/drone_relay.log

# Set proper ownership (replace 'omermad' with current user)
CURRENT_USER=$(whoami)
sudo chown -R $CURRENT_USER:$CURRENT_USER /var/log/drone_relay

# Set proper permissions
sudo chmod 755 /var/log/drone_relay
sudo chmod 644 /var/log/drone_relay.log

echo "Log permissions set for user: $CURRENT_USER"
echo "Log directory: /var/log/drone_relay"
echo "Log file: /var/log/drone_relay.log"
