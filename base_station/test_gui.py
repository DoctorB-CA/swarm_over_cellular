#!/usr/bin/env python3
"""
Simple test launcher to debug Qt issues
"""

import sys
import os

# Set environment variables before any imports
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = ''
os.environ['QT_DEBUG_PLUGINS'] = '0'
os.environ['OPENCV_IO_ENABLE_OPENEXR'] = '0'

def test_qt():
    """Test basic Qt functionality"""
    print("Testing Qt imports...")
    
    try:
        from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel
        from PyQt5.QtCore import Qt
        print("✓ PyQt5 imports successful")
        
        print("Creating QApplication...")
        app = QApplication(sys.argv)
        print("✓ QApplication created")
        
        print("Creating test window...")
        window = QMainWindow()
        window.setWindowTitle("Test Window")
        window.resize(300, 200)
        
        label = QLabel("Qt is working!")
        label.setAlignment(Qt.AlignCenter)
        window.setCentralWidget(label)
        
        print("✓ Test window created")
        print("Showing window...")
        window.show()
        
        print("✓ GUI test successful!")
        print("Closing in 2 seconds...")
        
        # Close after 2 seconds for testing
        from PyQt5.QtCore import QTimer
        timer = QTimer()
        timer.timeout.connect(app.quit)
        timer.start(2000)
        
        return app.exec_()
        
    except Exception as e:
        print(f"✗ Qt test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

def test_opencv():
    """Test OpenCV imports"""
    print("\nTesting OpenCV imports...")
    
    try:
        import cv2
        print("✓ OpenCV import successful")
        print(f"OpenCV version: {cv2.__version__}")
        return True
    except Exception as e:
        print(f"✗ OpenCV test failed: {e}")
        return False

def main():
    """Main test function"""
    print("=== Qt/OpenCV Compatibility Test ===\n")
    
    # Test OpenCV first
    if not test_opencv():
        return 1
    
    # Test Qt
    return test_qt()

if __name__ == '__main__':
    sys.exit(main())
