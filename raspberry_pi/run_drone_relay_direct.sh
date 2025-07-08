#!/bin/bash
echo "Running drone relay directly (for testing)..."
echo "Press Ctrl+C to stop"
echo ""

cd "$(dirname "$0")"
python3 drone_relay.py
