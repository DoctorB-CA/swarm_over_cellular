#!/bin/bash
"""
Raspberry Pi Drone Relay - Quick Start Script

This script provides easy commands for managing the drone relay system.
Run without arguments to see available options.
"""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RELAY_DIR="/opt/drone_relay"

show_help() {
    echo "Raspberry Pi Drone Relay - Quick Start"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Setup Commands:"
    echo "  install     - Install the relay system (requires sudo)"
    echo "  configure   - Configure network interfaces (requires sudo)"
    echo ""
    echo "Service Commands:"
    echo "  start       - Start the relay service"
    echo "  stop        - Stop the relay service"
    echo "  restart     - Restart the relay service"
    echo "  status      - Show service status and logs"
    echo "  logs        - Show live logs"
    echo ""
    echo "Testing Commands:"
    echo "  test        - Test relay connectivity"
    echo "  simulate    - Run full simulation (base + drone + monitor)"
    echo "  monitor     - Monitor relay traffic"
    echo ""
    echo "Configuration Commands:"
    echo "  config      - Edit relay configuration"
    echo "  network     - Configure network settings"
    echo "  firewall    - Setup basic firewall rules"
    echo ""
    echo "Information Commands:"
    echo "  info        - Show system information"
    echo "  stats       - Show relay statistics"
    echo ""
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo "This command requires root privileges. Please run with sudo:"
        echo "sudo $0 $1"
        exit 1
    fi
}

case "$1" in
    "install")
        check_root
        echo "Installing Raspberry Pi Drone Relay..."
        bash "$SCRIPT_DIR/setup_relay.sh"
        ;;
    
    "configure")
        check_root
        echo "Configuring network interfaces..."
        python3 "$SCRIPT_DIR/network_config_tool.py"
        ;;
    
    "start")
        echo "Starting drone relay service..."
        sudo systemctl start drone-relay.service
        sleep 2
        sudo systemctl status drone-relay.service --no-pager
        ;;
    
    "stop")
        echo "Stopping drone relay service..."
        sudo systemctl stop drone-relay.service
        sudo systemctl status drone-relay.service --no-pager
        ;;
    
    "restart")
        echo "Restarting drone relay service..."
        sudo systemctl restart drone-relay.service
        sleep 2
        sudo systemctl status drone-relay.service --no-pager
        ;;
    
    "status")
        echo "=== Drone Relay Service Status ==="
        sudo systemctl status drone-relay.service --no-pager
        echo ""
        echo "=== Recent Logs ==="
        sudo journalctl -u drone-relay.service -n 20 --no-pager
        echo ""
        echo "=== Network Status ==="
        echo "Listening ports:"
        sudo netstat -ulnp | grep python3 || echo "No Python processes listening"
        ;;
    
    "logs")
        echo "=== Live Drone Relay Logs ==="
        echo "Press Ctrl+C to exit"
        sudo journalctl -u drone-relay.service -f
        ;;
    
    "test")
        echo "Testing relay connectivity..."
        python3 "$SCRIPT_DIR/relay_test.py" test
        ;;
    
    "simulate")
        echo "Starting full relay simulation..."
        echo "This will simulate base station, drone, and monitor traffic"
        echo "Press Ctrl+C to stop"
        python3 "$SCRIPT_DIR/relay_test.py" full
        ;;
    
    "monitor")
        echo "Monitoring relay traffic..."
        echo "Press Ctrl+C to stop"
        python3 "$SCRIPT_DIR/relay_test.py" monitor
        ;;
    
    "config")
        if [ -f "$RELAY_DIR/relay_config.py" ]; then
            echo "Opening relay configuration..."
            sudo nano "$RELAY_DIR/relay_config.py"
            echo ""
            echo "Configuration updated. Restart service to apply changes:"
            echo "$0 restart"
        else
            echo "Relay not installed. Run '$0 install' first."
        fi
        ;;
    
    "network")
        check_root
        python3 "$SCRIPT_DIR/network_config_tool.py"
        ;;
    
    "firewall")
        check_root
        echo "Setting up basic firewall rules..."
        bash "$SCRIPT_DIR/../setup_firewall.sh" 2>/dev/null || {
            echo "Firewall script not found. Setting up basic rules..."
            
            # Basic firewall rules
            iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
            iptables -A INPUT -i lo -j ACCEPT
            iptables -A INPUT -p tcp --dport 22 -j ACCEPT
            iptables -A INPUT -p udp --dport 8888 -j ACCEPT
            iptables -A INPUT -p udp --dport 8889 -j ACCEPT
            iptables -A INPUT -p udp --dport 5000 -j ACCEPT
            iptables -A INPUT -p udp --dport 11111 -j ACCEPT
            iptables -A FORWARD -j ACCEPT
            
            echo "Basic firewall rules applied."
            echo "To make persistent: sudo apt install iptables-persistent"
        }
        ;;
    
    "info")
        echo "=== Raspberry Pi Drone Relay Information ==="
        echo ""
        echo "System Information:"
        echo "  Hostname: $(hostname)"
        echo "  OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
        echo "  Uptime: $(uptime -p)"
        echo ""
        echo "Network Interfaces:"
        ip addr show | grep -A 2 "^[0-9]:" | grep -E "(inet |^[0-9]:)" | while read line; do
            if [[ $line =~ ^[0-9]: ]]; then
                echo "  $line"
            elif [[ $line =~ inet ]]; then
                echo "    $line"
            fi
        done
        echo ""
        echo "Service Status:"
        services=("drone-relay" "hostapd" "dnsmasq" "dhcpcd")
        for service in "${services[@]}"; do
            status=$(systemctl is-active $service 2>/dev/null || echo "inactive")
            echo "  $service: $status"
        done
        echo ""
        if [ -f "$RELAY_DIR/relay_config.py" ]; then
            echo "Relay Installation: ✓ Installed at $RELAY_DIR"
        else
            echo "Relay Installation: ✗ Not installed"
        fi
        ;;
    
    "stats")
        echo "=== Relay Statistics ==="
        if systemctl is-active drone-relay.service >/dev/null; then
            echo "Service is running. Recent activity:"
            sudo journalctl -u drone-relay.service --since "1 hour ago" | grep -E "(commands|telemetry|video|statistics)" | tail -10
        else
            echo "Service is not running."
        fi
        echo ""
        echo "Network Activity:"
        if command -v vnstat >/dev/null; then
            vnstat -i eth0 --short 2>/dev/null || echo "No eth0 statistics available"
            vnstat -i wlan0 --short 2>/dev/null || echo "No wlan0 statistics available"
        else
            echo "Install vnstat for network statistics: sudo apt install vnstat"
        fi
        ;;
    
    *)
        show_help
        ;;
esac
