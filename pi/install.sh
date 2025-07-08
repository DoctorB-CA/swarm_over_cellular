#!/bin/bash
"""
Installation script for Drone Communication Bridge on Raspberry Pi
This script automates the setup process for the communication bridge
"""

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/home/pi/drones_over_cellular"
SERVICE_NAME="drone-bridge"
USER="pi"
GROUP="pi"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root"
        print_status "Please run as user 'pi': ./install.sh"
        exit 1
    fi
}

# Function to check if running on Raspberry Pi
check_raspberry_pi() {
    if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
        print_warning "This script is designed for Raspberry Pi"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Function to update system
update_system() {
    print_status "Updating system packages..."
    sudo apt update && sudo apt upgrade -y
    print_success "System updated"
}

# Function to install dependencies
install_dependencies() {
    print_status "Installing system dependencies..."
    
    # System packages
    sudo apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        git \
        wget \
        curl \
        modemmanager \
        network-manager \
        nmap \
        tcpdump \
        iotop \
        htop
    
    print_success "System dependencies installed"
}

# Function to install Python dependencies
install_python_dependencies() {
    print_status "Installing Python dependencies..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "$INSTALL_DIR/venv" ]; then
        python3 -m venv "$INSTALL_DIR/venv"
    fi
    
    # Activate virtual environment and install packages
    source "$INSTALL_DIR/venv/bin/activate"
    pip install --upgrade pip
    
    # Install required packages
    pip install \
        numpy \
        opencv-python \
        pyserial \
        requests \
        psutil
    
    deactivate
    print_success "Python dependencies installed"
}

# Function to setup directories and permissions
setup_directories() {
    print_status "Setting up directories and permissions..."
    
    # Ensure install directory exists and has correct ownership
    sudo mkdir -p "$INSTALL_DIR"
    sudo chown -R "$USER:$GROUP" "$INSTALL_DIR"
    
    # Create log directory
    sudo mkdir -p /var/log/drone-bridge
    sudo chown "$USER:$GROUP" /var/log/drone-bridge
    
    # Make scripts executable
    chmod +x "$INSTALL_DIR/pi/communication_bridge.py"
    chmod +x "$INSTALL_DIR/pi/run_bridge.sh"
    chmod +x "$INSTALL_DIR/pi/install.sh"
    
    print_success "Directories and permissions configured"
}

# Function to install systemd service
install_service() {
    print_status "Installing systemd service..."
    
    # Update service file with correct paths
    sed "s|/home/pi/drones_over_cellular|$INSTALL_DIR|g" \
        "$INSTALL_DIR/pi/drone-bridge.service" | \
        sudo tee /etc/systemd/system/drone-bridge.service > /dev/null
    
    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable drone-bridge
    
    print_success "Service installed and enabled"
}

# Function to configure network settings
configure_network() {
    print_status "Configuring network settings..."
    
    # Check if NetworkManager is running
    if ! systemctl is-active --quiet NetworkManager; then
        print_warning "NetworkManager is not running. Starting it..."
        sudo systemctl enable NetworkManager
        sudo systemctl start NetworkManager
    fi
    
    # Configure firewall rules if ufw is installed
    if command -v ufw >/dev/null 2>&1; then
        print_status "Configuring firewall rules..."
        sudo ufw allow 8889/udp comment "Drone commands"
        sudo ufw allow 8888/udp comment "Drone telemetry"
        sudo ufw allow 8890/udp comment "Drone video"
        sudo ufw allow 5000/udp comment "RTP video"
        print_success "Firewall rules configured"
    fi
    
    print_success "Network configuration completed"
}

# Function to create configuration files
create_configs() {
    print_status "Creating configuration files..."
    
    # Create environment file for service
    sudo tee /etc/default/drone-bridge > /dev/null << EOF
# Environment file for Drone Communication Bridge
PYTHONPATH=$INSTALL_DIR
PYTHONUNBUFFERED=1
LOG_LEVEL=INFO
EOF
    
    # Create logrotate configuration
    sudo tee /etc/logrotate.d/drone-bridge > /dev/null << EOF
/var/log/drone-bridge/*.log /tmp/communication_bridge*.log {
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
    
    print_success "Configuration files created"
}

# Function to test installation
test_installation() {
    print_status "Testing installation..."
    
    # Test Python imports
    if python3 -c "import socket, threading, json, time, logging" 2>/dev/null; then
        print_success "Python dependencies OK"
    else
        print_error "Python dependency test failed"
        return 1
    fi
    
    # Test bridge script syntax
    if python3 -m py_compile "$INSTALL_DIR/pi/communication_bridge.py"; then
        print_success "Bridge script syntax OK"
    else
        print_error "Bridge script has syntax errors"
        return 1
    fi
    
    # Test service file
    if sudo systemctl is-enabled drone-bridge >/dev/null 2>&1; then
        print_success "Service is enabled"
    else
        print_error "Service is not enabled"
        return 1
    fi
    
    print_success "Installation tests passed"
}

# Function to show post-installation instructions
show_instructions() {
    print_success "Installation completed successfully!"
    echo
    print_status "Next steps:"
    echo "1. Edit configuration: nano $INSTALL_DIR/pi/bridge_config.py"
    echo "2. Configure your network settings (cellular APN, IPs, etc.)"
    echo "3. Start the service: sudo systemctl start drone-bridge"
    echo "4. Check status: sudo systemctl status drone-bridge"
    echo "5. View logs: sudo journalctl -u drone-bridge -f"
    echo
    print_status "Manual operation:"
    echo "- Start: $INSTALL_DIR/pi/run_bridge.sh start"
    echo "- Stop:  $INSTALL_DIR/pi/run_bridge.sh stop"
    echo "- Status: $INSTALL_DIR/pi/run_bridge.sh status"
    echo
    print_status "Documentation: $INSTALL_DIR/pi/README.md"
}

# Main installation function
main() {
    echo "========================================"
    echo "Drone Communication Bridge Installer"
    echo "========================================"
    echo
    
    # Pre-installation checks
    check_root
    check_raspberry_pi
    
    # Confirm installation
    print_status "This will install the Drone Communication Bridge on this Raspberry Pi"
    print_status "Installation directory: $INSTALL_DIR"
    read -p "Continue with installation? (Y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        print_status "Installation cancelled"
        exit 0
    fi
    
    # Installation steps
    update_system
    install_dependencies
    install_python_dependencies
    setup_directories
    install_service
    configure_network
    create_configs
    test_installation
    show_instructions
    
    echo
    print_success "Installation completed successfully!"
    print_status "Reboot is recommended before first use"
}

# Run main function
main "$@"
