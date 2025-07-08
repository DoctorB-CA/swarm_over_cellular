#!/bin/bash
"""
Installation and setup script for the Raspberry Pi drone relay system.

This script installs dependencies and configures the Raspberry Pi to run
the drone communication relay.
"""

# Exit on any error
set -e

echo "=== Raspberry Pi Drone Relay Setup ==="
echo "This script will install and configure the drone relay system"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run this script as root (use sudo)"
    exit 1
fi

# Update system
echo "Updating system packages..."
apt update && apt upgrade -y

# Install Python and pip if not already installed
echo "Installing Python dependencies..."
apt install -y python3 python3-pip python3-venv

# Install FFmpeg for video relay
echo "Installing FFmpeg..."
apt install -y ffmpeg

# Install system utilities
echo "Installing system utilities..."
apt install -y htop iotop net-tools tcpdump

# Create application directory
APP_DIR="/opt/drone_relay"
echo "Creating application directory: $APP_DIR"
mkdir -p $APP_DIR

# Copy application files
echo "Copying application files..."
cp drone_relay.py $APP_DIR/
cp relay_config.py $APP_DIR/
chmod +x $APP_DIR/drone_relay.py

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv $APP_DIR/venv

# Install Python packages
echo "Installing Python packages..."
$APP_DIR/venv/bin/pip install --upgrade pip

# Create log directory
echo "Creating log directory..."
mkdir -p /var/log/drone_relay
chown pi:pi /var/log/drone_relay

# Create systemd service file
echo "Creating systemd service..."
cat > /etc/systemd/system/drone-relay.service << 'EOF'
[Unit]
Description=Drone Communication Relay
After=network.target
Wants=network.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/opt/drone_relay
ExecStart=/opt/drone_relay/venv/bin/python /opt/drone_relay/drone_relay.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment variables
Environment=PYTHONPATH=/opt/drone_relay
Environment=PATH=/opt/drone_relay/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

[Install]
WantedBy=multi-user.target
EOF

# Create log rotation configuration
echo "Setting up log rotation..."
cat > /etc/logrotate.d/drone-relay << 'EOF'
/var/log/drone_relay.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    copytruncate
    su pi pi
}
EOF

# Set proper permissions
echo "Setting permissions..."
chown -R pi:pi $APP_DIR
chmod +x $APP_DIR/drone_relay.py

# Create configuration backup
echo "Creating configuration backup..."
cp $APP_DIR/relay_config.py $APP_DIR/relay_config.py.backup

# Enable and start service
echo "Enabling drone relay service..."
systemctl daemon-reload
systemctl enable drone-relay.service

# Create management scripts
echo "Creating management scripts..."

# Start script
cat > /home/pi/start_drone_relay.sh << 'EOF'
#!/bin/bash
echo "Starting drone relay service..."
sudo systemctl start drone-relay.service
sleep 2
sudo systemctl status drone-relay.service
EOF

# Stop script
cat > /home/pi/stop_drone_relay.sh << 'EOF'
#!/bin/bash
echo "Stopping drone relay service..."
sudo systemctl stop drone-relay.service
sudo systemctl status drone-relay.service
EOF

# Status script
cat > /home/pi/check_drone_relay.sh << 'EOF'
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
EOF

# Log viewer script
cat > /home/pi/view_drone_logs.sh << 'EOF'
#!/bin/bash
echo "=== Live Drone Relay Logs ==="
echo "Press Ctrl+C to exit"
sudo journalctl -u drone-relay.service -f
EOF

# Configuration editor script
cat > /home/pi/edit_drone_config.sh << 'EOF'
#!/bin/bash
echo "Opening drone relay configuration..."
echo "Remember to restart the service after making changes!"
sudo nano /opt/drone_relay/relay_config.py
echo ""
echo "Restart service with: sudo systemctl restart drone-relay.service"
EOF

# Make scripts executable
chmod +x /home/pi/*.sh
chown pi:pi /home/pi/*.sh

# Create network configuration helper
cat > /home/pi/configure_network.sh << 'EOF'
#!/bin/bash
echo "=== Network Configuration Helper ==="
echo ""
echo "Current network configuration:"
ip addr show

echo ""
echo "To configure static IP addresses, edit /etc/dhcpcd.conf"
echo "Example configuration for dual network setup:"
echo ""
echo "# Base station network interface (e.g., eth0)"
echo "interface eth0"
echo "static ip_address=10.0.0.4/24"
echo "static routers=10.0.0.1"
echo "static domain_name_servers=8.8.8.8"
echo ""
echo "# Drone network interface (e.g., wlan0 as hotspot)"
echo "interface wlan0"
echo "static ip_address=192.168.4.1/24"
echo "nohook wpa_supplicant"
echo ""
echo "After editing, restart networking:"
echo "sudo systemctl restart dhcpcd"
EOF

chmod +x /home/pi/configure_network.sh
chown pi:pi /home/pi/configure_network.sh

# Install network monitoring tools
echo "Installing network monitoring tools..."
apt install -y iftop nethogs vnstat

# Enable IP forwarding (for routing between networks)
echo "Enabling IP forwarding..."
echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf

# Create firewall rules script
cat > /home/pi/setup_firewall.sh << 'EOF'
#!/bin/bash
echo "Setting up basic firewall rules for drone relay..."

# Allow established connections
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# Allow loopback
iptables -A INPUT -i lo -j ACCEPT

# Allow SSH (be careful!)
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# Allow drone communication ports
iptables -A INPUT -p udp --dport 8888 -j ACCEPT  # Telemetry
iptables -A INPUT -p udp --dport 8889 -j ACCEPT  # Commands
iptables -A INPUT -p udp --dport 5000 -j ACCEPT  # RTP Video
iptables -A INPUT -p udp --dport 11111 -j ACCEPT # Drone video

# Allow forwarding between interfaces
iptables -A FORWARD -j ACCEPT

# Drop everything else
iptables -A INPUT -j DROP

echo "Firewall rules applied. To make persistent, install iptables-persistent:"
echo "sudo apt install iptables-persistent"
echo "sudo netfilter-persistent save"
EOF

chmod +x /home/pi/setup_firewall.sh
chown pi:pi /home/pi/setup_firewall.sh

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Management scripts created in /home/pi/:"
echo "  start_drone_relay.sh    - Start the relay service"
echo "  stop_drone_relay.sh     - Stop the relay service"
echo "  check_drone_relay.sh    - Check service status and logs"
echo "  view_drone_logs.sh      - View live logs"
echo "  edit_drone_config.sh    - Edit configuration"
echo "  configure_network.sh    - Network setup helper"
echo "  setup_firewall.sh       - Basic firewall setup"
echo ""
echo "Configuration file: /opt/drone_relay/relay_config.py"
echo "Log file: /var/log/drone_relay.log"
echo ""
echo "Next steps:"
echo "1. Configure network interfaces (run ./configure_network.sh for help)"
echo "2. Edit relay configuration: ./edit_drone_config.sh"
echo "3. Start the relay: ./start_drone_relay.sh"
echo "4. Check status: ./check_drone_relay.sh"
echo ""
echo "The service will automatically start on boot."
