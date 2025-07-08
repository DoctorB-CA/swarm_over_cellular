#!/bin/bash
"""
Utility script to manage the communication bridge and avoid port conflicts
"""

# Function to kill processes using specific ports
kill_port_processes() {
    echo "Checking for processes using bridge ports..."
    
    # Bridge ports from config
    BRIDGE_PORTS=(8889 9888 9890 6000)
    
    for port in "${BRIDGE_PORTS[@]}"; do
        echo "Checking port $port..."
        # Find processes using the port
        PIDS=$(lsof -ti:$port 2>/dev/null)
        if [ ! -z "$PIDS" ]; then
            echo "Found processes using port $port: $PIDS"
            echo "Killing processes..."
            kill -9 $PIDS 2>/dev/null || true
            sleep 1
        else
            echo "Port $port is free"
        fi
    done
}

# Function to start the bridge
start_bridge() {
    echo "Starting communication bridge..."
    cd "$(dirname "$0")"
    python3 communication_bridge.py --verbose "$@"
}

# Function to restart the bridge
restart_bridge() {
    echo "Restarting communication bridge..."
    kill_port_processes
    sleep 2
    start_bridge "$@"
}

# Function to show port status
show_ports() {
    echo "Port status:"
    BRIDGE_PORTS=(8889 9888 9890 6000)
    for port in "${BRIDGE_PORTS[@]}"; do
        echo -n "Port $port: "
        if lsof -ti:$port >/dev/null 2>&1; then
            echo "IN USE by PID $(lsof -ti:$port)"
        else
            echo "FREE"
        fi
    done
}

# Main script logic
case "$1" in
    start)
        start_bridge "${@:2}"
        ;;
    stop)
        kill_port_processes
        ;;
    restart)
        restart_bridge "${@:2}"
        ;;
    status)
        show_ports
        ;;
    clean)
        echo "Cleaning up all bridge-related processes..."
        pkill -f communication_bridge.py || true
        kill_port_processes
        echo "Cleanup complete"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|clean} [bridge_options]"
        echo ""
        echo "Commands:"
        echo "  start     - Start the communication bridge"
        echo "  stop      - Stop processes using bridge ports"
        echo "  restart   - Clean stop and start the bridge"
        echo "  status    - Show port usage status"
        echo "  clean     - Kill all bridge processes and free ports"
        echo ""
        echo "Examples:"
        echo "  $0 start                    # Start with default settings"
        echo "  $0 start --verbose          # Start with verbose logging"
        echo "  $0 restart --drone-ip 192.168.1.100"
        echo "  $0 status                   # Check port status"
        exit 1
        ;;
esac
