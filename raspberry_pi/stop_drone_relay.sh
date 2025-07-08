#!/bin/bash
echo "Stopping drone relay service..."
sudo systemctl stop drone-relay.service
sudo systemctl status drone-relay.service
