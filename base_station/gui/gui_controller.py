import sys
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import QTimer, QThread, pyqtSlot

from base_station.connection.drone_comm import DroneComm
from .gui_components import (
    VideoFeedWidget, ConnectionWidget,
    FlightControlsWidget, AdvancedControlsWidget
)

class DroneGUIController(QMainWindow):
    """Main controller for the drone GUI application"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize UI components first
        self.init_ui()
        
        # Create the communication layer after UI is initialized
        self.drone_comm = None
        self.init_communication()
        
        # Create a fallback timer for UI updates when no telemetry is received
        self.fallback_timer = QTimer()
        self.fallback_timer.timeout.connect(self.fallback_update)
        self.fallback_timer.start(100)  # 10 fps
    
    def init_communication(self):
        """Initialize the communication layer in the main thread"""
        try:
            self.drone_comm = DroneComm()
            
            # Connect signals from communication layer
            self.drone_comm.video_frame_received.connect(self.handle_video_frame)
            self.drone_comm.connection_status_changed.connect(self.handle_connection_status)
            
        except Exception as e:
            print(f"Error initializing communication: {e}")
            self.drone_comm = None
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle('Enhanced Drone Control')
        self.setGeometry(100, 100, 900, 700)
        
        # Main layout
        main_layout = QHBoxLayout()
        
        # Create left panel (video + connection settings)
        left_panel = QVBoxLayout()
        
        # Video feed
        self.video_widget = VideoFeedWidget(self)
        
        # Connection settings
        self.connection_widget = ConnectionWidget(self, self.toggle_connection)
        
        # Add to left panel
        left_panel.addWidget(self.video_widget.get_widget(), 4)
        left_panel.addWidget(self.connection_widget.get_widget(), 1)
        
        # Create right panel (controls only)
        right_panel = QVBoxLayout()
        
        # Flight controls
        self.flight_controls = FlightControlsWidget(
            self, self.takeoff, self.land, self.move
        )
        
        # Advanced controls
        self.advanced_controls = AdvancedControlsWidget(
            self, self.emergency_stop
        )
        
        # Add to right panel
        right_panel.addWidget(self.flight_controls.get_widget())
        right_panel.addWidget(self.advanced_controls.get_widget())
        
        # Add panels to main layout
        main_layout.addLayout(left_panel, 3)
        main_layout.addLayout(right_panel, 1)
        
        # Set the main layout
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # Set initial state of control buttons
        self.update_control_buttons(False)
    
    def update_control_buttons(self, enabled):
        """Enable or disable control buttons based on connection status"""
        self.flight_controls.set_enabled(enabled)
        self.advanced_controls.set_enabled(enabled)
    
    #
    # Communication handlers
    #
    
    def toggle_connection(self):
        """Connect to or disconnect from the drone"""
        if not self.drone_comm:
            print("Error: Communication layer not initialized")
            return
            
        if not self.drone_comm.connected:
            # Update connection parameters
            params = self.connection_widget.get_connection_params()
            self.drone_comm.ip = params['ip']
            self.drone_comm.command_port = params['command_port']
            self.drone_comm.telemetry_port = params['telemetry_port']
            self.drone_comm.rtp_video_port = params['video_port']  # Now using RTP video port
            
            # Connect
            if self.drone_comm.connect():
                self.connection_widget.set_button_text("Disconnect")
                self.update_control_buttons(True)
            else:
                # Connection failed, update handled by signal
                pass
        else:
            # Disconnect
            self.drone_comm.disconnect()
            self.connection_widget.set_button_text("Connect")
            self.update_control_buttons(False)
    
    def handle_connection_status(self, connected, message):
        """Handle connection status changes"""
        self.connection_widget.update_status(connected, message)
    
    def handle_video_frame(self, frame):
        """Handle incoming video frames"""
        self.video_widget.update_frame(frame)
    
    #
    # Drone control functions
    #
    
    def takeoff(self):
        """Command the drone to take off"""
        self.drone_comm.send_command("takeoff")
    
    def land(self):
        """Command the drone to land"""
        self.drone_comm.send_command("land")
    
    def move(self, direction):
        """Command the drone to move in a direction"""
        distance = self.advanced_controls.get_distance()
        self.drone_comm.send_command(f"{direction} {distance}")
    
    def emergency_stop(self):
        """Emergency stop - land immediately"""
        self.drone_comm.send_command("land")  # Replace with emergency command if available
    
    #
    # Simulation and fallback updates
    #
    
    def fallback_update(self):
        """Fallback update for when no telemetry is being received"""
        if not self.drone_comm.connected:
            # Generate simulated video frame when not connected
            self.video_widget.generate_simulated_frame()
    
    def closeEvent(self, event):
        """Clean up when window is closed"""
        self.fallback_timer.stop()
        
        if self.drone_comm.connected:
            self.drone_comm.disconnect()
        
        event.accept()
