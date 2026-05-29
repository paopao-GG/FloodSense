import os
import sys
import time
import cv2
import numpy as np
import requests
import board
import adafruit_dht
import RPi.GPIO as GPIO
import ai_edge_litert.interpreter as tflite
from smbus2 import SMBus
import cloudinary
import cloudinary.uploader

# =====================================================================
# 1. HARDWARE PIN & CLOUD CONFIGURATION
# =====================================================================
# DHT11 Data Pin connected to Board Pin GPIO 4 (D4)
dht_device = adafruit_dht.DHT11(board.D4)

# Ultrasonic Sensor GPIO Mapping (BCM Numbers)
TRIG_PIN = 23        # GPIO 23
ECHO_PIN = 24        # GPIO 24

# Ultrasonic Distance Trigger Threshold (in centimeters)
# Wakes up the CNN when water rises closer than this value
DISTANCE_THRESHOLD_CM = 30.0  

# Firebase REST API Realtime Database Node Endpoint URL
# (Replace 'your-project-id' with your actual Firebase project ID)
WEB_URL = "https://floodsense-ffce3-default-rtdb.asia-southeast1.firebasedatabase.app/flood_telemetry.json"

# Cloudinary credentials — copy from cloudinary.com → Dashboard
CLOUDINARY_CLOUD_NAME = "dqcqkpjcc"
CLOUDINARY_API_KEY    = "284736694491497"
CLOUDINARY_API_SECRET = "eZH4JZWT-q5kAhrriQ59J3yxCtE"

cloudinary.config(
    cloud_name = CLOUDINARY_CLOUD_NAME,
    api_key    = CLOUDINARY_API_KEY,
    api_secret = CLOUDINARY_API_SECRET,
    secure     = True
)

# I2C LCD Parameters
I2C_BUS = 1
LCD_ADDRESS = 0x27  # Standard PCF8574 backpack address
LCD_WIDTH = 20      # Maximum character count per line (20x4 display)

# =====================================================================
# 2. TFLITE CNN MODEL SETTINGS
# =====================================================================
MODEL_PATH = "flood_model_quantized.tflite"

# Verified Class Labels matched to your model's real training output index
LABELS = {
    0: "Ignore (Metadata)",
    1: "Normal Conditions",       # Index 1 = Safe
    2: "FLOOD ALERT ACTIVE"       # Index 2 = Flood
}

# =====================================================================
# 3. CAMERA HARDWARE HOOK
# =====================================================================
# 🛑 FLIP THIS TO 'True' TOMORROW WHEN YOUR HARDWARE SENSOR ARRIVES!
CAMERA_AVAILABLE = True 

# =====================================================================
# LOW-LEVEL I2C LCD DRIVER ROUTINES
# =====================================================================
# PCF8574 backpack bit positions
LCD_RS = 0x01        # Register select (0=command, 1=data)
LCD_EN = 0x04        # Enable strobe
LCD_BACKLIGHT = 0x08 # Backlight on

def _lcd_send_nibble(bus, nibble, rs):
    data = (nibble & 0xF0) | LCD_BACKLIGHT | rs
    bus.write_byte(LCD_ADDRESS, data | LCD_EN)
    time.sleep(0.00005)
    bus.write_byte(LCD_ADDRESS, data)
    time.sleep(0.0001)

def lcd_write_cmd(cmd):
    try:
        with SMBus(I2C_BUS) as bus:
            _lcd_send_nibble(bus, cmd & 0xF0, 0)
            _lcd_send_nibble(bus, (cmd << 4) & 0xF0, 0)
    except Exception as e:
        print(f"[Hardware Note] LCD command failed: {e}")

def lcd_write_char(char):
    try:
        val = ord(char)
        with SMBus(I2C_BUS) as bus:
            _lcd_send_nibble(bus, val & 0xF0, LCD_RS)
            _lcd_send_nibble(bus, (val << 4) & 0xF0, LCD_RS)
    except Exception:
        pass

def lcd_init():
    try:
        with SMBus(I2C_BUS) as bus:
            # Force 8-bit mode reset three times, then switch to 4-bit
            for _ in range(3):
                _lcd_send_nibble(bus, 0x30, 0)
                time.sleep(0.005)
            _lcd_send_nibble(bus, 0x20, 0)
        lcd_write_cmd(0x28) # 2 lines, 5x8 font
        lcd_write_cmd(0x0C) # Display on, cursor off
        lcd_write_cmd(0x06) # Entry mode: left-to-right
        lcd_write_cmd(0x01) # Clear display
        time.sleep(0.002)
    except Exception as e:
        print(f"[Hardware Note] LCD screen bypassed or unattached: {e}")

def lcd_display_text(text, line):
    try:
        # 20x4 HD44780 DDRAM line addresses
        line_addresses = {1: 0x80, 2: 0xC0, 3: 0x94, 4: 0xD4}
        if line not in line_addresses:
            return
        lcd_write_cmd(line_addresses[line])
        text = text.ljust(LCD_WIDTH)[:LCD_WIDTH]
        for char in text:
            lcd_write_char(char)
    except Exception:
        pass

# =====================================================================
# SYSTEM HARDWARE CORE INITIALIZATION
# =====================================================================
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)

print("Powering up hardware peripherals...")
lcd_init()
lcd_display_text("FLOOD MONITOR SYSTEM", 1)
lcd_display_text("Initializing...", 2)
lcd_display_text("Loading AI model...", 3)
lcd_display_text("", 4)

print("Allocating memory arrays for Edge-AI TFLite engine...")
if not os.path.exists(MODEL_PATH):
    lcd_display_text("ERR: NO TFLITE", 1)
    raise FileNotFoundError(f"Missing custom model weights file: {MODEL_PATH}")

interpreter = tflite.Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
input_height = int(input_details[0]['shape'][1])
input_width = int(input_details[0]['shape'][2])

if CAMERA_AVAILABLE:
    from picamera2 import Picamera2
    picam = Picamera2()
    config = picam.create_video_configuration(main={"size": (640, 480)})
    picam.configure(config)
    picam.start()
    print("🎥 Camera sensor matrix active and locked.")
else:
    print("⚠️ STAGING SIMULATION MODE ACTIVE: Bypassing camera capture framework.")

# =====================================================================
# TELEMETRY LOGIC FUNCTIONS
# =====================================================================
def get_ultrasonic_distance():
    GPIO.output(TRIG_PIN, GPIO.LOW)
    time.sleep(0.05)
    GPIO.output(TRIG_PIN, GPIO.HIGH)
    time.sleep(0.00001)
    GPIO.output(TRIG_PIN, GPIO.LOW)

    timeout = time.time() + 0.04  # 40ms max wait (~6.8m range)
    start_time = time.time()
    while GPIO.input(ECHO_PIN) == 0:
        start_time = time.time()
        if start_time > timeout:
            return 999.0  # sensor not responding

    timeout = time.time() + 0.04
    stop_time = start_time
    while GPIO.input(ECHO_PIN) == 1:
        stop_time = time.time()
        if stop_time > timeout:
            return 999.0

    return ((stop_time - start_time) * 34300) / 2

def get_location():
    try:
        r = requests.get("http://ip-api.com/json", timeout=5)
        d = r.json()
        if d.get("status") == "success":
            return f"{d['city']}, {d['regionName']}, {d['country']}"
    except Exception:
        pass
    return "Unknown Location"

def upload_snapshot(frame, folder="flood_snapshots"):
    try:
        _, buf = cv2.imencode('.jpg', frame)
        result = cloudinary.uploader.upload(
            buf.tobytes(),
            folder=folder,
            resource_type="image"
        )
        print(f"📷 Snapshot uploaded: {result['secure_url']}")
        return result["secure_url"]
    except Exception as e:
        print(f"📷 Snapshot upload failed: {e}")
        return None

def send_firebase_payload(status, confidence, distance, temp, hum,
                          live_snapshot_url=None, flood_snapshot_url=None):
    payload = {
        "status": status,
        "cnn_confidence": f"{confidence:.1f}%",
        "water_depth_gap_cm": round(distance, 2),
        "temperature_c": temp,
        "humidity_percent": hum,
        "epoch_timestamp": time.time(),
        "location": LOCATION
    }
    if live_snapshot_url:
        payload["live_snapshot_url"] = live_snapshot_url
    if flood_snapshot_url:
        payload["flood_snapshot_url"] = flood_snapshot_url
    try:
        response = requests.put(WEB_URL, json=payload, timeout=2)
        print(f"📡 Firebase Cloud Updated! HTTP Status: {response.status_code}")
    except Exception as e:
        print(f"📡 Firebase Gateway Sync Error: {e}")

# =====================================================================
# 4. MAIN TELEMETRY WORKLOOP
# =====================================================================
print("📍 Detecting location...")
LOCATION = get_location()
print(f"📍 Location: {LOCATION}")

print("\n🚀 System active. Running monitoring routine loop...")
lcd_display_text("SYSTEM ARMED", 1)
lcd_display_text("MONITORING LIVE", 2)
lcd_display_text("", 3)
lcd_display_text("", 4)

last_snapshot_time     = 0
live_snapshot_url      = None
last_flood_snapshot_url = None  # persists the most recent confirmed flood snapshot

try:
    while True:
        # A. Fetch Climate Telemetry via CircuitPython Wrapper
        try:
            temperature = dht_device.temperature
            humidity = dht_device.humidity
            if temperature is None or humidity is None:
                temperature, humidity = 0.0, 0.0
        except RuntimeError:
            temperature, humidity = 0.0, 0.0

        # B. Fetch Water Line Distance via Pulse Timings
        try:
            distance = get_ultrasonic_distance()
        except Exception:
            distance = 999.0

        print(f"Metrics -> Distance: {distance:.1f}cm | Temp: {temperature}°C | Hum: {humidity}%")

        system_status  = "Normal Conditions"
        cnn_confidence = 0.0

        # B2. Periodic live snapshot every 30 seconds (independent of flood status)
        if CAMERA_AVAILABLE and (time.time() - last_snapshot_time >= 30):
            raw_frame = picam.capture_array()
            live_snapshot_url = upload_snapshot(raw_frame, folder="flood_live")
            last_snapshot_time = time.time()

        # C. Hardware Threshold Gating Trigger Evaluation Check
        if distance <= DISTANCE_THRESHOLD_CM:
            print(f"⚠️ THRESHOLD BREACHED ({distance:.1f}cm) -> Running CNN Verification...")
            lcd_display_text("LEVEL BREACHED", 1)

            if CAMERA_AVAILABLE:
                raw_frame = picam.capture_array()

                resized = cv2.resize(raw_frame, (input_width, input_height))
                normalized_image = resized.astype(np.float32) / 255.0
                input_tensor = np.expand_dims(normalized_image, axis=0)

                interpreter.set_tensor(input_details[0]['index'], input_tensor)
                interpreter.invoke()

                predictions = interpreter.get_tensor(output_details[0]['index'])[0]
                top_prediction_idx = int(np.argmax(predictions))
                cnn_confidence = float(predictions[top_prediction_idx]) * 100
                system_status = LABELS[top_prediction_idx]

                if system_status == "FLOOD ALERT ACTIVE":
                    last_flood_snapshot_url = upload_snapshot(raw_frame, folder="flood_alerts")
            else:
                system_status = "FLOOD ALERT ACTIVE"
                cnn_confidence = 100.0
                print("Pre-Stage System: Automatically asserting FLOOD confirmation flag.")

            print(f"CNN Verdict Result: {system_status} ({cnn_confidence:.1f}%)")

            # D. Update LCD status
            if system_status == "FLOOD ALERT ACTIVE":
                lcd_display_text("!! FLOOD ALERT !!", 1)
            else:
                lcd_display_text("STATUS: NORMAL", 1)
        else:
            lcd_display_text("STATUS: NORMAL", 1)

        # Always push live telemetry every cycle so webapp stays current
        send_firebase_payload(system_status, cnn_confidence, distance, temperature, humidity,
                              live_snapshot_url, last_flood_snapshot_url)

        # E. Push live telemetry across lines 2-4
        lcd_display_text(f"Water:  {distance:.1f} cm", 2)
        lcd_display_text(f"Temp:   {temperature} C", 3)
        lcd_display_text(f"Humidity: {humidity} %", 4)
        
        # Delay rate before running the next check cycle
        time.sleep(2)

except KeyboardInterrupt:
    print("\nExecution broken by manual user override request.")
finally:
    # Safely clear system interrupts, thread channels, and unlatch voltage pins
    GPIO.cleanup()
    if CAMERA_AVAILABLE:
        picam.stop()
    lcd_display_text("SYSTEM OFFLINE", 1)
    lcd_display_text("GPIO DEALLOCATED", 2)
    lcd_display_text("", 3)
    lcd_display_text("", 4)
    print("Cleanup pipeline complete. RPi safely offline.")
