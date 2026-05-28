import os
import cv2
import numpy as np
import ai_edge_litert.interpreter as tflite
from picamera2 import Picamera2

# 1. Path Configuration
MODEL_PATH = "flood_model_quantized.tflite"

print("--- Initializing Flood Monitor LIVE System ---")
print(f"Current Working Directory: {os.getcwd()}")

# Verify model file exists before booting camera hardware
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"CRITICAL ERROR: Could not find '{MODEL_PATH}'!")

# 2. Load TFLite Model & Allocate Memory
interpreter = tflite.Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

input_height = int(input_details[0]['shape'][1])
input_width = int(input_details[0]['shape'][2])

# Dataset Index Class Labels
# Updated Class Labels to match your model's actual training output indices
LABELS = {
    0: "Ignore (Metadata)",
    1: "Normal Conditions - Dry/Safe",   # Swapped from Flood to Safe
    2: "FLOOD DETECTED - ALERT ACTIVE"   # Swapped from Safe to Flood
}

# 3. Initialize Picamera2 Interface
print("Configuring 5MP camera hardware...")
picam = Picamera2()
config = picam.create_video_configuration(main={"size": (640, 480)})
picam.configure(config)
picam.start()

print("\n========================================================")
print("RPi Cam Module Online. Running live inference loop...")
print("👉 Press 'q' while clicking the video window to STOP.")
print("========================================================\n")

try:
    while True:
        # Capture raw frame array directly from the camera stream
        raw_frame = picam.capture_array()
        
        if raw_frame is None:
            print("Warning: Dropped frame from camera sensor.")
            continue
            
        # Preprocessing Pipeline
        resized = cv2.resize(raw_frame, (input_width, input_height))
        
        # Picamera2 outputs standard RGB. If your model expects standard RGB,
        # we don't need cv2.cvtColor(resized, cv2.COLOR_BGR2RGB) here!
        normalized_image = resized.astype(np.float32) / 255.0
        input_tensor = np.expand_dims(normalized_image, axis=0)
        
        # Run Inference
        interpreter.set_tensor(input_details[0]['index'], input_tensor)
        interpreter.invoke()
        
        # Extract Predictions
        predictions = interpreter.get_tensor(output_details[0]['index'])[0]
        
        # Type-casting to fix Thonny strict warning flags
        top_prediction_idx = int(np.argmax(predictions))
        confidence_score = float(predictions[top_prediction_idx])
        
        # Visual UI Setup
        status_text = LABELS[top_prediction_idx]
        display_string = f"{status_text} ({confidence_score * 100:.1f}%)"
        
        # Green for Safe, Red for Flood
        color = (0, 0, 255) if top_prediction_idx == 1 else (0, 255, 0)
        
        # Convert frame to BGR format *only* for OpenCV to draw/display it correctly on monitor
        display_frame = cv2.cvtColor(raw_frame, cv2.COLOR_RGB2BGR)
        cv2.putText(display_frame, display_string, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        
        # Show the live stream window
        cv2.imshow("Live RPi Flood Monitoring Feed", display_frame)
        
        # Break the infinite loop instantly if user presses 'q' key
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("User requested shutdown.")
            break

finally:
    # CRUCIAL: Always turn off the physical camera power lines, even if code crashes!
    print("\nShutting down camera array safely...")
    picam.stop()
    cv2.destroyAllWindows()
    print("System safely offline.")