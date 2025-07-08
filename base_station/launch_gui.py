"""
Launch script for the enhanced drone GUI application.

This script imports and runs the drone GUI application from the gui package.
"""

import sys
import os

# Fix Qt plugin conflicts before any Qt imports
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = ''
os.environ['QT_DEBUG_PLUGINS'] = '0'

# Prevent OpenCV from loading Qt plugins that conflict with PyQt5
os.environ['OPENCV_IO_ENABLE_OPENEXR'] = '0'

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import order matters for Qt/OpenCV conflicts
# Import PyQt first
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread

# Configure OpenCV to not use Qt backend
import cv2
cv2.setUseOptimized(True)
# Disable OpenCV's Qt integration to avoid conflicts
try:
    cv2.namedWindow("test")
    cv2.destroyWindow("test")
except:
    pass

# Finally import our application
from gui import DroneGUIController

def main():
    """Main application entry point with proper error handling"""
    try:
        # Create application instance
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(True)
        
        # Set application properties
        app.setApplicationName("Drone Control System")
        app.setApplicationVersion("1.0")
        
        # Create and show GUI
        gui = DroneGUIController()
        gui.show()
        
        # Start event loop
        return app.exec_()
        
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())