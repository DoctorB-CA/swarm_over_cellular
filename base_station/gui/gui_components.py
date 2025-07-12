from PyQt5.QtWidgets import (QLabel, QPushButton, QSlider, QProgressBar, 
                             QLineEdit, QGroupBox, QGridLayout, QVBoxLayout, QHBoxLayout)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap, QIntValidator, qRgb

# Import network configuration
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_station.connection.network_config import DRONE_IP, COMMAND_PORT, TELEMETRY_PORT, VIDEO_PORT, RTP_VIDEO_PORT

class VideoFeedWidget:
    """Widget for displaying video feed from the drone"""
    
    def __init__(self, parent):
        # Video feed 
        self.video_feed = QLabel(parent)
        self.video_feed.setStyleSheet("background-color: black; border: 2px solid gray;")
        self.video_feed.setMinimumSize(640, 480)
        self.video_feed.setScaledContents(True)  # Scale content to fit
        
        # Create an empty pixmap with "No Video Signal" text
        self.create_no_signal_pixmap()
        
        # Frame counter for fallback video simulation
        self.frame_count = 0
        
    def create_no_signal_pixmap(self):
        """Create a 'No Video Signal' placeholder"""
        from PyQt5.QtGui import QPainter, QFont
        empty_pixmap = QPixmap(640, 480)
        empty_pixmap.fill(Qt.black)
        
        painter = QPainter(empty_pixmap)
        painter.setPen(Qt.white)
        painter.setFont(QFont("Arial", 16))
        painter.drawText(empty_pixmap.rect(), Qt.AlignCenter, "No Video Signal\nWaiting for RTP stream from relay...\nConnect to start video feed")
        painter.end()
        
        self.video_feed.setPixmap(empty_pixmap)
        
    def get_widget(self):
        return self.video_feed
        
    def update_frame(self, frame):
        """Update with a received QImage frame"""
        # Ensure frame is valid
        if frame.isNull():
            return
            
        # Convert to pixmap and scale properly
        pixmap = QPixmap.fromImage(frame)
        
        # Get widget size and frame size
        widget_size = self.video_feed.size()
        frame_size = pixmap.size()
        
        # Scale to fit widget while maintaining aspect ratio
        scaled_pixmap = pixmap.scaled(
            widget_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        
        self.video_feed.setPixmap(scaled_pixmap)
        
    def generate_simulated_frame(self):
        """Generate a simulated frame for testing"""
        self.frame_count += 1
        width, height = 640, 480
        image = QImage(width, height, QImage.Format_RGB888)
        
        # Create a more sophisticated test pattern
        for x in range(0, width, 20):
            for y in range(0, height, 20):
                # Create a moving pattern
                if (x // 20 + y // 20 + self.frame_count // 5) % 2 == 0:
                    color = qRgb(50, 50, 100)  # Dark blue
                else:
                    color = qRgb(100, 150, 200)  # Light blue
                    
                for i in range(20):
                    for j in range(20):
                        if x+i < width and y+j < height:
                            image.setPixel(x+i, y+j, color)
        
        # Add text overlay for simulation
        from PyQt5.QtGui import QPainter, QFont
        pixmap = QPixmap.fromImage(image)
        painter = QPainter(pixmap)
        painter.setPen(Qt.white)
        painter.setFont(QFont("Arial", 12))
        painter.drawText(10, 30, f"Simulated FFmpeg RTP Stream - Frame {self.frame_count}")
        painter.end()
                                
        # Display simulated frame
        self.video_feed.setPixmap(pixmap)
        return image


class ConnectionWidget:
    """Widget for drone connection settings"""
    
    def __init__(self, parent, on_connect_clicked):
        # Connection settings
        self.group = QGroupBox("Connection Settings", parent)
        layout = QGridLayout()
        
        # IP input
        layout.addWidget(QLabel("Drone IP:"), 0, 0)
        self.ip_input = QLineEdit(DRONE_IP)
        layout.addWidget(self.ip_input, 0, 1)
        
        # Command port
        layout.addWidget(QLabel("Command Port:"), 1, 0)
        self.command_port_input = QLineEdit(str(COMMAND_PORT))
        self.command_port_input.setValidator(QIntValidator(1, 65535))
        layout.addWidget(self.command_port_input, 1, 1)
        
        # Telemetry port
        layout.addWidget(QLabel("Telemetry Port:"), 2, 0)
        self.telemetry_port_input = QLineEdit(str(TELEMETRY_PORT))
        self.telemetry_port_input.setValidator(QIntValidator(1, 65535))
        layout.addWidget(self.telemetry_port_input, 2, 1)

        # Video port
        layout.addWidget(QLabel("Video Port:"), 3, 0)
        self.video_port_input = QLineEdit(str(RTP_VIDEO_PORT))
        self.video_port_input.setValidator(QIntValidator(1, 65535))
        layout.addWidget(self.video_port_input, 3, 1)
        
        # Connect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(on_connect_clicked)
        layout.addWidget(self.connect_btn, 4, 0, 1, 2)
        
        # Status label
        self.status_label = QLabel("Not Connected")
        self.status_label.setStyleSheet("color: red;")
        layout.addWidget(self.status_label, 5, 0, 1, 2)
        
        self.group.setLayout(layout)
    
    def get_widget(self):
        return self.group
    
    def get_connection_params(self):
        """Get connection parameters entered by user"""
        return {
            'ip': self.ip_input.text(),
            'command_port': int(self.command_port_input.text()),
            'telemetry_port': int(self.telemetry_port_input.text()),
            'video_port': int(self.video_port_input.text())
        }
    
    def set_button_text(self, text):
        """Set the text of the connect button"""
        self.connect_btn.setText(text)
    
    def update_status(self, connected, message):
        """Update the connection status display"""
        self.status_label.setText(message)
        if connected:
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setStyleSheet("color: red;")


class FlightControlsWidget:
    """Widget containing flight control buttons"""
    
    def __init__(self, parent, on_takeoff, on_land, on_move):
        self.group = QGroupBox("Flight Controls", parent)
        layout = QGridLayout()
        
        # Takeoff and land
        self.takeoff_btn = QPushButton("Takeoff")
        self.takeoff_btn.clicked.connect(on_takeoff)
        layout.addWidget(self.takeoff_btn, 0, 1)
        
        self.land_btn = QPushButton("Land")
        self.land_btn.clicked.connect(on_land)
        layout.addWidget(self.land_btn, 4, 1)
        
        # Directional controls
        self.forward_btn = QPushButton("Forward")
        self.forward_btn.clicked.connect(lambda: on_move("forward"))
        layout.addWidget(self.forward_btn, 1, 1)
        
        self.backward_btn = QPushButton("Backward")
        self.backward_btn.clicked.connect(lambda: on_move("backward"))
        layout.addWidget(self.backward_btn, 3, 1)
        
        self.left_btn = QPushButton("Left")
        self.left_btn.clicked.connect(lambda: on_move("left"))
        layout.addWidget(self.left_btn, 2, 0)
        
        self.right_btn = QPushButton("Right")
        self.right_btn.clicked.connect(lambda: on_move("right"))
        layout.addWidget(self.right_btn, 2, 2)
        
        # Video control buttons
        self.video_on_btn = QPushButton("Video ON")
        self.video_on_btn.clicked.connect(lambda: on_move("streamon"))
        self.video_on_btn.setStyleSheet("background-color: green; color: white;")
        layout.addWidget(self.video_on_btn, 5, 0)
        
        self.video_off_btn = QPushButton("Video OFF")
        self.video_off_btn.clicked.connect(lambda: on_move("streamoff"))
        self.video_off_btn.setStyleSheet("background-color: red; color: white;")
        layout.addWidget(self.video_off_btn, 5, 2)
        
        self.group.setLayout(layout)
    
    def get_widget(self):
        return self.group
    
    def set_enabled(self, enabled):
        """Enable or disable all control buttons"""
        self.takeoff_btn.setEnabled(enabled)
        self.land_btn.setEnabled(enabled)
        self.forward_btn.setEnabled(enabled)
        self.backward_btn.setEnabled(enabled)
        self.left_btn.setEnabled(enabled)
        self.right_btn.setEnabled(enabled)
        self.video_on_btn.setEnabled(enabled)
        self.video_off_btn.setEnabled(enabled)


class AdvancedControlsWidget:
    """Widget containing advanced drone controls"""
    
    def __init__(self, parent, on_emergency):
        self.group = QGroupBox("Advanced Controls", parent)
        layout = QGridLayout()
        
        # Distance slider
        layout.addWidget(QLabel("Distance (cm):"), 0, 0)
        self.distance_slider = QSlider(Qt.Horizontal)
        self.distance_slider.setMinimum(10)
        self.distance_slider.setMaximum(100)
        self.distance_slider.setValue(20)
        self.distance_slider.setTickPosition(QSlider.TicksBelow)
        self.distance_slider.setTickInterval(10)
        layout.addWidget(self.distance_slider, 0, 1)
        
        self.distance_label = QLabel("20")
        layout.addWidget(self.distance_label, 0, 2)
        self.distance_slider.valueChanged.connect(
            lambda value: self.distance_label.setText(str(value)))
        
        # Emergency stop
        self.emergency_btn = QPushButton("EMERGENCY STOP")
        self.emergency_btn.setStyleSheet("background-color: red; color: white; font-weight: bold;")
        self.emergency_btn.clicked.connect(on_emergency)
        layout.addWidget(self.emergency_btn, 1, 0, 1, 3)
        
        self.group.setLayout(layout)
    
    def get_widget(self):
        return self.group
    
    def get_distance(self):
        """Get the currently selected distance value"""
        return self.distance_slider.value()
    
    def set_enabled(self, enabled):
        """Enable or disable all advanced controls"""
        self.distance_slider.setEnabled(enabled)
        self.emergency_btn.setEnabled(enabled)
