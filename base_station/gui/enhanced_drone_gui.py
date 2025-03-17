"""
Enhanced Drone GUI - Main application file

This is the main entry point for the Enhanced Drone GUI application.
It separates the communication layer from the GUI components for better maintainability.
"""

import sys
import os
from PyQt5.QtWidgets import QApplication

if __name__ == '__main__':
    # When run directly, use absolute imports
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    from gui.gui_controller import DroneGUIController
    
    app = QApplication(sys.argv)
    gui = DroneGUIController()
    gui.show()
    sys.exit(app.exec_())
else:
    # When imported as a module, use relative imports
    from .gui_controller import DroneGUIController
