"""
Drone GUI package

This package contains modules for the enhanced drone GUI application:
- drone_comm: Communication layer for drone control
- gui_components: Reusable GUI components 
- gui_controller: Main controller connecting GUI and communication
"""

from connection.drone_comm import DroneComm
from .gui_controller import DroneGUIController