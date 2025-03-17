"""
Launch script for the enhanced drone GUI application.

This script imports and runs the drone GUI application from the gui package.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import order matters for Qt/OpenCV conflicts
# Import PyQt first
from PyQt5.QtWidgets import QApplication

# Then import OpenCV
import cv2  

# Finally import our application
from gui import DroneGUIController

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = DroneGUIController()
    gui.show()
    sys.exit(app.exec_())