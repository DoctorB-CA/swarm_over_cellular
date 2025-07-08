#!/usr/bin/env python3
"""
Raspberry Pi Network Configuration Tool

This tool helps configure the Raspberry Pi network interfaces for optimal
drone relay operation. It can set up both wired and wireless interfaces.
"""

import subprocess
import sys
import os
import json
from typing import Dict, List, Optional

class NetworkConfigurator:
    """Network configuration helper for Raspberry Pi"""
    
    def __init__(self):
        self.dhcpcd_config = "/etc/dhcpcd.conf"
        self.hostapd_config = "/etc/hostapd/hostapd.conf"
        self.dnsmasq_config = "/etc/dnsmasq.conf"
    
    def get_current_interfaces(self) -> Dict:
        """Get current network interface information"""
        try:
            # Get interface list
            result = subprocess.run(['ip', 'addr', 'show'], 
                                  capture_output=True, text=True)
            
            interfaces = {}
            current_interface = None
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line.startswith(('1:', '2:', '3:', '4:', '5:')):
                    # New interface
                    parts = line.split()
                    if len(parts) >= 2:
                        current_interface = parts[1].rstrip(':')
                        interfaces[current_interface] = {
                            'name': current_interface,
                            'state': 'DOWN' if 'state DOWN' in line else 'UP',
                            'addresses': []
                        }
                elif 'inet ' in line and current_interface:
                    # IP address
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == 'inet' and i + 1 < len(parts):
                            interfaces[current_interface]['addresses'].append(parts[i + 1])
            
            return interfaces
            
        except Exception as e:
            print(f"Error getting interfaces: {e}")
            return {}
    
    def configure_static_interface(self, interface: str, ip: str, 
                                 gateway: Optional[str] = None,
                                 dns: Optional[str] = None):
        """Configure a static IP for an interface"""
        
        print(f"Configuring static IP for {interface}: {ip}")
        
        # Read current dhcpcd.conf
        config_lines = []
        if os.path.exists(self.dhcpcd_config):
            with open(self.dhcpcd_config, 'r') as f:
                config_lines = f.readlines()
        
        # Remove existing configuration for this interface
        new_config = []
        skip_section = False
        
        for line in config_lines:
            if line.strip().startswith(f'interface {interface}'):
                skip_section = True
                continue
            elif line.strip().startswith('interface ') and skip_section:
                skip_section = False
            elif line.strip().startswith('static ') and skip_section:
                continue
            elif line.strip().startswith('nohook ') and skip_section:
                continue
                
            if not skip_section:
                new_config.append(line)
        
        # Add new configuration
        new_config.append(f'\n# Configuration for {interface}\n')
        new_config.append(f'interface {interface}\n')
        new_config.append(f'static ip_address={ip}\n')
        
        if gateway:
            new_config.append(f'static routers={gateway}\n')
        
        if dns:
            new_config.append(f'static domain_name_servers={dns}\n')
        
        # Write updated configuration
        with open(self.dhcpcd_config, 'w') as f:
            f.writelines(new_config)
        
        print(f"Updated {self.dhcpcd_config}")
    
    def setup_wifi_hotspot(self, interface: str = 'wlan0', 
                          ssid: str = 'DroneRelay',
                          password: str = 'DroneRelay123',
                          ip: str = '192.168.4.1/24'):
        """Setup WiFi hotspot for drone communication"""
        
        print(f"Setting up WiFi hotspot on {interface}")
        
        # Configure static IP
        self.configure_static_interface(interface, ip)
        
        # Add nohook for wpa_supplicant
        with open(self.dhcpcd_config, 'a') as f:
            f.write(f'nohook wpa_supplicant\n')
        
        # Configure hostapd
        hostapd_config = f"""
# Hotspot configuration for drone relay
interface={interface}
driver=nl80211
ssid={ssid}
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase={password}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
"""
        
        os.makedirs(os.path.dirname(self.hostapd_config), exist_ok=True)
        with open(self.hostapd_config, 'w') as f:
            f.write(hostapd_config.strip())
        
        # Configure dnsmasq for DHCP
        dnsmasq_config = f"""
# DHCP configuration for drone hotspot
interface={interface}
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
"""
        
        with open(self.dnsmasq_config, 'w') as f:
            f.write(dnsmasq_config.strip())
        
        # Enable services
        subprocess.run(['systemctl', 'enable', 'hostapd'])
        subprocess.run(['systemctl', 'enable', 'dnsmasq'])
        
        print("WiFi hotspot configured")
        print(f"SSID: {ssid}")
        print(f"Password: {password}")
        print(f"IP: {ip}")
    
    def apply_configuration(self):
        """Apply network configuration changes"""
        print("Applying network configuration...")
        
        try:
            # Restart dhcpcd
            subprocess.run(['systemctl', 'restart', 'dhcpcd'], check=True)
            print("Restarted dhcpcd service")
            
            # Restart hostapd if configured
            if os.path.exists(self.hostapd_config):
                subprocess.run(['systemctl', 'restart', 'hostapd'], check=False)
                print("Restarted hostapd service")
            
            # Restart dnsmasq if configured
            if os.path.exists(self.dnsmasq_config):
                subprocess.run(['systemctl', 'restart', 'dnsmasq'], check=False)
                print("Restarted dnsmasq service")
            
            print("Configuration applied successfully")
            
        except subprocess.CalledProcessError as e:
            print(f"Error applying configuration: {e}")
    
    def show_status(self):
        """Show current network status"""
        print("=== Current Network Status ===")
        
        interfaces = self.get_current_interfaces()
        for name, info in interfaces.items():
            if name != 'lo':  # Skip loopback
                print(f"\nInterface: {name}")
                print(f"  State: {info['state']}")
                if info['addresses']:
                    for addr in info['addresses']:
                        print(f"  IP: {addr}")
                else:
                    print("  IP: Not configured")
        
        print("\n=== Service Status ===")
        for service in ['dhcpcd', 'hostapd', 'dnsmasq']:
            try:
                result = subprocess.run(['systemctl', 'is-active', service], 
                                      capture_output=True, text=True)
                status = result.stdout.strip()
                print(f"  {service}: {status}")
            except:
                print(f"  {service}: unknown")

def main():
    """Main configuration menu"""
    if os.geteuid() != 0:
        print("This script must be run as root (use sudo)")
        sys.exit(1)
    
    config = NetworkConfigurator()
    
    while True:
        print("\n=== Raspberry Pi Network Configuration ===")
        print("1. Show current network status")
        print("2. Configure wired interface (eth0) for base station")
        print("3. Configure WiFi hotspot for drone")
        print("4. Apply configuration changes")
        print("5. Quick setup (typical drone relay configuration)")
        print("6. Exit")
        
        choice = input("\nSelect option (1-6): ").strip()
        
        if choice == '1':
            config.show_status()
        
        elif choice == '2':
            print("\nConfiguring wired interface for base station connection...")
            ip = input("Enter IP address (e.g., 10.0.0.4/24): ").strip()
            gateway = input("Enter gateway IP (e.g., 10.0.0.1) or press Enter to skip: ").strip()
            dns = input("Enter DNS server (e.g., 8.8.8.8) or press Enter to skip: ").strip()
            
            gateway = gateway if gateway else None
            dns = dns if dns else None
            
            config.configure_static_interface('eth0', ip, gateway, dns)
            print("Wired interface configured")
        
        elif choice == '3':
            print("\nConfiguring WiFi hotspot for drone connection...")
            ssid = input("Enter WiFi network name (default: DroneRelay): ").strip()
            password = input("Enter WiFi password (default: DroneRelay123): ").strip()
            ip = input("Enter hotspot IP (default: 192.168.4.1/24): ").strip()
            
            ssid = ssid if ssid else 'DroneRelay'
            password = password if password else 'DroneRelay123'
            ip = ip if ip else '192.168.4.1/24'
            
            config.setup_wifi_hotspot('wlan0', ssid, password, ip)
        
        elif choice == '4':
            config.apply_configuration()
        
        elif choice == '5':
            print("\nQuick setup for typical drone relay configuration...")
            print("This will configure:")
            print("- eth0: 10.0.0.4/24 (base station network)")
            print("- wlan0: 192.168.4.1/24 (drone hotspot)")
            
            confirm = input("Continue? (y/N): ").strip().lower()
            if confirm == 'y':
                # Configure wired interface
                config.configure_static_interface('eth0', '10.0.0.4/24', '10.0.0.1', '8.8.8.8')
                
                # Configure WiFi hotspot
                config.setup_wifi_hotspot()
                
                print("\nQuick setup complete!")
                print("Apply changes with option 4")
        
        elif choice == '6':
            print("Exiting...")
            break
        
        else:
            print("Invalid option, please try again")

if __name__ == '__main__':
    main()
