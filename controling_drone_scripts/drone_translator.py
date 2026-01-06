#!/usr/bin/env python3
"""
Drone Command Translator
Translates keyboard inputs to drone-specific commands
Supports multiple drone types
"""

class DroneTranslator:
    """Base class for drone command translation"""
    
    def __init__(self, drone_type="tello"):
        self.drone_type = drone_type
        self.current_speed = 50  # Default speed (20-100 for Tello)
        
    def translate(self, key_command):
        """
        Translate a key command to drone-specific command
        Returns the actual command string to send to the drone
        """
        if self.drone_type == "tello":
            return self._translate_tello(key_command)
        else:
            return None
    
    def _translate_tello(self, key_command):
        """Translate commands for Tello/Tello EDU drones"""
        
        # Movement commands with distance
        movement_map = {
            'forward': f'forward {self.current_speed}',
            'backward': f'back {self.current_speed}',
            'left': f'left {self.current_speed}',
            'right': f'right {self.current_speed}',
            'up': f'up {self.current_speed}',
            'down': f'down {self.current_speed}',
        }
        
        # Rotation commands
        rotation_map = {
            'rotate_left': 'ccw 45',  # Counter-clockwise 45 degrees
            'rotate_right': 'cw 45',   # Clockwise 45 degrees
        }
        
        # Control commands
        control_map = {
            'takeoff': 'takeoff',
            'land': 'land',
            'emergency': 'emergency',
            'stop': 'stop',
        }
        
        # Query commands
        query_map = {
            'battery': 'battery?',
            'speed': 'speed?',
            'time': 'time?',
            'height': 'height?',
            'temp': 'temp?',
        }
        
        # Speed adjustment
        if key_command.startswith('set_speed_'):
            speed = int(key_command.split('_')[-1])
            self.current_speed = max(20, min(100, speed))  # Clamp between 20-100
            return f'speed {self.current_speed}'
        
        # Check all command maps
        for cmd_map in [movement_map, rotation_map, control_map, query_map]:
            if key_command in cmd_map:
                return cmd_map[key_command]
        
        # If no match, return None
        return None
    
    def get_speed(self):
        """Get current speed setting"""
        return self.current_speed
    
    def set_speed(self, speed):
        """Set movement speed (20-100 for Tello)"""
        self.current_speed = max(20, min(100, speed))
