#!/bin/bash
echo "Starting drone relay service..."
sudo systemctl start drone-relay.service
sleep 2
sudo systemctl status drone-relay.service
