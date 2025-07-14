#!/usr/bin/env bash
set -e

# 1) Activate venv
source "$(dirname "$0")/../venv/bin/activate"

# 1a) Point DISPLAY at the Windows host (default gateway)
export DISPLAY=$(ip route | awk '/^default/ {print $3}'):0.0
export LIBGL_ALWAYS_INDIRECT=1

# 2) Clean slate for Qt
unset QT_PLUGIN_PATH
unset LD_LIBRARY_PATH

# 3) Only PyQt5 platform plugins
export QT_QPA_PLATFORM_PLUGIN_PATH="$VIRTUAL_ENV/lib/python3.10/site-packages/PyQt5/Qt5/plugins/platforms"
export QT_QPA_PLATFORM=xcb

# 4) Launch
python3 launch_gui.py
