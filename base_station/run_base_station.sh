#!/bin/bash
# Check if venv exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Get the parent directory of the project
PROJECT_DIR=$(dirname "$(pwd)")

# Temporarily rename OpenCV's plugins directory to avoid conflict
OPENCV_QT_DIR="$PROJECT_DIR/venv/lib/python3.12/site-packages/cv2/qt"
if [ -d "$OPENCV_QT_DIR" ]; then
    echo "Temporarily renaming OpenCV's Qt directory to avoid plugin conflicts..."
    mv "$OPENCV_QT_DIR" "${OPENCV_QT_DIR}_backup"
fi

# Set environment variables
export QT_QPA_PLATFORM_PLUGIN_PATH="$PROJECT_DIR/venv/lib/python3.12/site-packages/PyQt5/Qt5/plugins"
export QT_DEBUG_PLUGINS=0  # Disable debug output
export PYTHONPATH="$PROJECT_DIR"
export LD_LIBRARY_PATH="$PROJECT_DIR/venv/lib/python3.12/site-packages/PyQt5/Qt5/lib:$LD_LIBRARY_PATH"
export QT_THREAD_PRIORITY_SCALE=1
export QT_ENABLE_GLYPH_CACHE_WORKAROUND=1

echo "Starting Drone GUI..."

# Run the GUI
python3 launch_gui.py

# Restore OpenCV's plugins directory
if [ -d "${OPENCV_QT_DIR}_backup" ]; then
    echo "Restoring OpenCV's Qt directory..."
    mv "${OPENCV_QT_DIR}_backup" "$OPENCV_QT_DIR"
fi

echo "Environment variables used:"
echo "QT_QPA_PLATFORM_PLUGIN_PATH=$QT_QPA_PLATFORM_PLUGIN_PATH"
echo "PYTHONPATH=$PYTHONPATH"