#!/bin/bash

echo "Copying video test script to Pi..."
scp test_video_display.py pi@10.0.0.4:/tmp/

echo "Running video test on Pi..."
ssh pi@10.0.0.4 "cd /tmp && python3 test_video_display.py"

echo "Checking for saved test files..."
ssh pi@10.0.0.4 "ls -la /tmp/test_frame_*.jpg /tmp/drone_video_test.mp4 2>/dev/null || echo 'No test files found'"

echo "Done!"