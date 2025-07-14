#!/usr/bin/env bash
set -e

# 1) Activate venv
source "$(dirname "$0")/../venv/bin/activate"

# 2) DISPLAY is already set in your ~/.bashrc

# 3) Clean slate for Qt
unset QT_PLUGIN_PATH
unset LD_LIBRARY_PATH

# 4) Only platform plugins from PyQt5
export QT_QPA_PLATFORM_PLUGIN_PATH="$VIRTUAL_ENV/lib/python3.10/site-packages/PyQt5/Qt5/plugins/platforms"
export QT_QPA_PLATFORM=xcb

# 5) Launch
python3 launch_gui.py
