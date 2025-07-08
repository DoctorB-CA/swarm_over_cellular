#!/bin/bash
"""
Startup script for Communication Bridge on Raspberry Pi
This script sets up the environment and starts the communication bridge
"""

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRIDGE_SCRIPT="$SCRIPT_DIR/communication_bridge.py"
LOG_FILE="/tmp/bridge_startup.log"
PID_FILE="/tmp/bridge.pid"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to check if bridge is already running
is_bridge_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0  # Bridge is running
        else
            rm -f "$PID_FILE"  # Remove stale PID file
            return 1  # Bridge is not running
        fi
    fi
    return 1  # PID file doesn't exist
}

# Function to start the bridge
start_bridge() {
    log_message "Starting Communication Bridge..."
    
    # Check if already running
    if is_bridge_running; then
        log_message "Bridge is already running (PID: $(cat $PID_FILE))"
        return 0
    fi
    
    # Check if Python script exists
    if [ ! -f "$BRIDGE_SCRIPT" ]; then
        log_message "ERROR: Bridge script not found at $BRIDGE_SCRIPT"
        return 1
    fi
    
    # Make sure the script is executable
    chmod +x "$BRIDGE_SCRIPT"
    
    # Start the bridge in background
    nohup python3 "$BRIDGE_SCRIPT" --verbose > /tmp/communication_bridge_output.log 2>&1 &
    local bridge_pid=$!
    
    # Save PID
    echo "$bridge_pid" > "$PID_FILE"
    
    # Wait a moment and check if process is still running
    sleep 2
    if ps -p "$bridge_pid" > /dev/null 2>&1; then
        log_message "Bridge started successfully (PID: $bridge_pid)"
        return 0
    else
        log_message "ERROR: Bridge failed to start"
        rm -f "$PID_FILE"
        return 1
    fi
}

# Function to stop the bridge
stop_bridge() {
    log_message "Stopping Communication Bridge..."
    
    if is_bridge_running; then
        local pid=$(cat "$PID_FILE")
        log_message "Sending SIGTERM to process $pid"
        kill -TERM "$pid" 2>/dev/null
        
        # Wait for graceful shutdown
        local count=0
        while ps -p "$pid" > /dev/null 2>&1 && [ $count -lt 10 ]; do
            sleep 1
            ((count++))
        done
        
        # Force kill if still running
        if ps -p "$pid" > /dev/null 2>&1; then
            log_message "Force killing process $pid"
            kill -KILL "$pid" 2>/dev/null
        fi
        
        rm -f "$PID_FILE"
        log_message "Bridge stopped"
    else
        log_message "Bridge is not running"
    fi
}

# Function to check bridge status
status_bridge() {
    if is_bridge_running; then
        local pid=$(cat "$PID_FILE")
        log_message "Bridge is running (PID: $pid)"
        
        # Show some process info
        ps -p "$pid" -o pid,ppid,cmd,etime
        
        # Show last few log lines
        echo "Recent log entries:"
        tail -n 5 /tmp/communication_bridge.log 2>/dev/null || echo "No log file found"
    else
        log_message "Bridge is not running"
    fi
}

# Function to restart the bridge
restart_bridge() {
    log_message "Restarting Communication Bridge..."
    stop_bridge
    sleep 2
    start_bridge
}

# Function to show help
show_help() {
    echo "Usage: $0 {start|stop|restart|status|help}"
    echo ""
    echo "Commands:"
    echo "  start    - Start the communication bridge"
    echo "  stop     - Stop the communication bridge"
    echo "  restart  - Restart the communication bridge"
    echo "  status   - Show bridge status"
    echo "  help     - Show this help message"
    echo ""
    echo "Files:"
    echo "  Script:   $BRIDGE_SCRIPT"
    echo "  Log:      $LOG_FILE"
    echo "  PID:      $PID_FILE"
    echo "  Output:   /tmp/communication_bridge_output.log"
}

# Main script logic
case "$1" in
    start)
        start_bridge
        ;;
    stop)
        stop_bridge
        ;;
    restart)
        restart_bridge
        ;;
    status)
        status_bridge
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Invalid command: $1"
        show_help
        exit 1
        ;;
esac
