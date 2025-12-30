# Start (bring up wg0)
sudo systemctl start wg-quick@wg0

# Stop (bring down wg0)
sudo systemctl stop wg-quick@wg0

# Restart
sudo systemctl restart wg-quick@wg0

# Enable at boot + start now
sudo systemctl enable --now wg-quick@wg0

# Disable at boot (doesn't stop it)
sudo systemctl disable wg-quick@wg0

# Status
sudo systemctl status wg-quick@wg0 --no-pager

# Quick check
sudo wg show

