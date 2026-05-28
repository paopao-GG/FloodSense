import os
import cv2
import numpy as np
import ai_edge_litert.interpreter as tflite

# 1. Path Configuration
MODEL_PATH = "flood_model_quantized.tflite"
TEST_IMAGE_PATH = "test_scene.jpg"

print("--- Initializing Flood Monitor Offline Test ---")
print(f"Current Working Directory: {os.getcwd()}")

# Verify model file exists
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"CRITICAL ERROR: Could not find '{MODEL_PATH}'!")

# Verify image file exists before reading
if not os.path.exists(TEST_IMAGE_PATH):
    print("\n========================================================")
    print(f"CRITICAL ERROR: '{TEST_IMAGE_PATH}' was NOT found!")
    print("Please make sure the image file is named EXACTLY 'test_scene.jpg'")
    print("and is placed in the exact same folder as this script.")
    print("========================================================\n")
    raise FileNotFoundError(f"Missing input image: {TEST_IMAGE_PATH}")

# 2. Load TFLite Model & Allocate Memory
interpreter = tflite.Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

input_height = int(input_details[0]['shape'][1])
input_width = int(input_details[0]['shape'][2])

# Dataset Index Class Labels
LABELS = {
    0: "Ignore (Metadata)",
    1: "Normal Conditions - Dry/Safe",   # Swapped from Flood to Safe
    2: "FLOOD DETECTED - ALERT ACTIVE"   # Swapped from Safe to Flood
}

# 3. Process the Verified Image File
raw_frame = cv2.imread(TEST_IMAGE_PATH)

if raw_frame is None:
    raise ValueError("Error: OpenCV could not read the image file. It may be corrupted.")

# Preprocessing Pipeline
resized = cv2.resize(raw_frame, (input_width, input_height))
rgb_image = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
normalized_image = rgb_image.astype(np.float32) / 255.0
input_tensor = np.expand_dims(normalized_image, axis=0)

# Run Inference
interpreter.set_tensor(input_details[0]['index'], input_tensor)
interpreter.invoke()

# Extract Predictions
predictions = interpreter.get_tensor(output_details[0]['index'])[0]

# Fix Thonny Type Warning by casting index to a standard int
top_prediction_idx = int(np.argmax(predictions))
confidence_score = float(predictions[top_prediction_idx])

# Visual Configuration
status_text = LABELS[top_prediction_idx]
display_string = f"{status_text} ({confidence_score * 100:.1f}%)"
color = (0, 0, 255) if top_prediction_idx == 1 else (0, 255, 0)

# Draw results on display frame
display_frame = raw_frame.copy()
cv2.putText(display_frame, display_string, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

print("\n=== CLASSIFICATION MATRIX OVERVIEW ===")
print(f"Verdict: {display_string}")
print(f"Raw Probabilities -> [Class 0: {predictions[0]:.4f}, Class 1 (Flood): {predictions[1]:.4f}, Class 2 (Safe): {predictions[2]:.4f}]")

# Display Output Window
cv2.imshow("Flood Monitor Offline Test", display_frame)
print("\nClick on the image window and press any key to close it.")
cv2.waitKey(0)
cv2.destroyAllWindows()