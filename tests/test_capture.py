from src.capture.screen_capture import ScreenCapture
import os

print("Testing CLI Capture...")
capture = ScreenCapture()
try:
    # Capture a small region at top left
    img = capture.capture_region_via_cli(0, 0, 100, 100)
    print(f"Captured image size: {img.size}")
    img.save("test_capture.png")
    print("Saved test_capture.png")
except Exception as e:
    print(f"Capture failed: {e}")
