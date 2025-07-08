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
