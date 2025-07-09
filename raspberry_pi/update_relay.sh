#!/bin/bash
echo "Updating Raspberry Pi drone relay with JSON serialization fix..."

# Check if we're running as root for system file access
if [ "$EUID" -ne 0 ]; then
    echo "Please run this script as root (use sudo) to update system files"
    exit 1
fi

# Backup current files
echo "Creating backup of current installation..."
cp /opt/drone_relay/drone_relay.py /opt/drone_relay/drone_relay.py.backup.$(date +%Y%m%d_%H%M%S)
cp /opt/drone_relay/relay_config.py /opt/drone_relay/relay_config.py.backup.$(date +%Y%m%d_%H%M%S)

# Copy updated files
echo "Updating drone relay files..."
cp drone_relay.py /opt/drone_relay/
cp relay_config.py /opt/drone_relay/

# Set proper permissions
chown -R $(logname):$(logname) /opt/drone_relay/
chmod +x /opt/drone_relay/drone_relay.py

# Restart the service
echo "Restarting drone relay service..."
systemctl restart drone-relay.service

# Show status
echo ""
echo "Update complete! Service status:"
systemctl status drone-relay.service --no-pager -l

echo ""
echo "To monitor logs: journalctl -u drone-relay.service -f"
