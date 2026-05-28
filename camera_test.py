#!/usr/bin/env python3
"""
Raspberry Pi Camera live feed test script.
- Shows a live preview window for 30 seconds (or until Ctrl+C).
- Captures a snapshot on startup and saves it as camera_test_snapshot.jpg.
Press Ctrl+C to stop early.
"""

import time
import signal
import sys
from picamera2 import Picamera2
from picamera2.previews import QtPreview
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput

SNAPSHOT_PATH = "camera_test_snapshot.jpg"
PREVIEW_DURATION = 30  # seconds


def main():
    print("Initializing Raspberry Pi Camera...")
    cam = Picamera2()

    # Print detected camera info
    print(f"Camera model : {cam.camera_properties.get('Model', 'unknown')}")

    # Configure for still capture (used for snapshot) with a preview stream
    config = cam.create_preview_configuration(
        main={"size": (1280, 720)},
        lores={"size": (640, 360)},
        display="lores",
    )
    cam.configure(config)
    cam.start()

    # Give the sensor a moment to settle
    time.sleep(2)

    # Capture a snapshot
    cam.capture_file(SNAPSHOT_PATH)
    print(f"Snapshot saved to {SNAPSHOT_PATH}")

    # Start live preview using rpicam / Qt window
    print(f"Live preview running for {PREVIEW_DURATION}s — press Ctrl+C to stop early.")
    print("(A preview window should appear on your display / VNC session.)")

    try:
        cam.start_preview(QtPreview())
        for remaining in range(PREVIEW_DURATION, 0, -1):
            print(f"  {remaining}s remaining...", end="\r", flush=True)
            time.sleep(1)
        print("\nPreview finished.")
    except KeyboardInterrupt:
        print("\nStopped by user.")
    except Exception as exc:
        # QtPreview needs a display; fall back to a headless frame-grab loop
        print(f"Qt preview unavailable ({exc}), running headless frame test instead.")
        cam.stop_preview()
        headless_test(cam)
    finally:
        cam.stop_preview()
        cam.stop()
        print("Camera released.")


def headless_test(cam):
    """Grab frames in a loop and print basic stats (no display required)."""
    import numpy as np

    print("Grabbing 30 frames and reporting brightness (headless mode)...")
    for i in range(1, 31):
        frame = cam.capture_array("main")
        mean_brightness = int(np.mean(frame))
        print(f"  Frame {i:02d}: shape={frame.shape}  mean brightness={mean_brightness}")
        time.sleep(1)
    print("Headless test complete.")


if __name__ == "__main__":
    main()
