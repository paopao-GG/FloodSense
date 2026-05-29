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

# Firebase REST API Realtime Database — base URL + derived endpoints
FIREBASE_BASE = "https://floodsense-ffce3-default-rtdb.asia-southeast1.firebasedatabase.app"
WEB_URL       = f"{FIREBASE_BASE}/flood_telemetry.json"
SNAP_BASE_URL = f"{FIREBASE_BASE}/snapshots"

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

def upload_snapshot(frame, folder="flood_snapshots", overwrite_id=None):
    try:
        _, buf = cv2.imencode('.jpg', frame)
        kwargs = {"folder": folder, "resource_type": "image"}
        if overwrite_id:
            # Overwrite a fixed slot — no storage accumulation for live feed
            kwargs["public_id"] = overwrite_id
            kwargs["overwrite"] = True
            kwargs["invalidate"] = True  # bust Cloudinary CDN cache
        result = cloudinary.uploader.upload(buf.tobytes(), **kwargs)
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
LOCATION = "Felicidad Subdivision, Sugcad, Polangui, Albay"

print("\n🚀 System active. Running monitoring routine loop...")
lcd_display_text("SYSTEM ARMED", 1)
lcd_display_text("MONITORING LIVE", 2)
lcd_display_text("", 3)
lcd_display_text("", 4)

last_snapshot_time      = 0
live_snapshot_url       = None
last_flood_snapshot_url = None  # persists the most recent confirmed flood snapshot
slot_index              = 0     # cycles 0-719, one slot per 30s upload → 6 hours of history

# Flood-status latch: once a flood is confirmed, hold "FLOOD ALERT ACTIVE" until the
# ultrasonic stops breaching for FLOOD_HOLD_SECONDS. Prevents the status from flapping
# every cycle and from getting stuck on "flood" after the water recedes.
FLOOD_HOLD_SECONDS  = 30
flood_latched       = False
last_trigger_time   = 0.0
last_cnn_confidence = 0.0

# DHT11 noise filtering — EMA smoothing + last-valid holdover
EMA_ALPHA      = 0.3   # 0=no smoothing, 1=no memory; 0.3 is a good balance for DHT11
last_valid_temp = None
last_valid_hum  = None
ema_temp        = None
ema_hum         = None

try:
    while True:
        # A. Fetch Climate Telemetry via CircuitPython Wrapper
        try:
            raw_temp = dht_device.temperature
            raw_hum  = dht_device.humidity
            if raw_temp is not None and raw_hum is not None and raw_temp != 0 and raw_hum != 0:
                last_valid_temp = raw_temp
                last_valid_hum  = raw_hum
        except RuntimeError:
            pass  # DHT11 checksum error — keep last valid reading

        # Hold last valid reading instead of zeroing on failure
        temperature = last_valid_temp if last_valid_temp is not None else 0.0
        humidity    = last_valid_hum  if last_valid_hum  is not None else 0.0

        # EMA smoothing — dampens sensor jitter without introducing lag
        if temperature != 0:
            ema_temp    = temperature if ema_temp is None else EMA_ALPHA * temperature + (1 - EMA_ALPHA) * ema_temp
            temperature = round(ema_temp, 1)
        if humidity != 0:
            ema_hum  = humidity if ema_hum is None else EMA_ALPHA * humidity + (1 - EMA_ALPHA) * ema_hum
            humidity = round(ema_hum, 1)

        # B. Fetch Water Line Distance via Pulse Timings
        try:
            distance = get_ultrasonic_distance()
        except Exception:
            distance = 999.0

        print(f"Metrics -> Distance: {distance:.1f}cm | Temp: {temperature}°C | Hum: {humidity}%")

        # Carry the last detection confidence while the flood latch is held; otherwise
        # no CNN ran this cycle, so report 0%.
        cnn_confidence = last_cnn_confidence if flood_latched else 0.0

        # B2. Periodic live snapshot every 30 seconds (independent of flood status)
        if CAMERA_AVAILABLE and (time.time() - last_snapshot_time >= 30):
            raw_frame = picam.capture_array()
            slot_id = f"slot_{slot_index:03d}"
            live_snapshot_url = upload_snapshot(
                raw_frame,
                folder="flood_live",
                overwrite_id=f"flood_live/{slot_id}"
            )
            if live_snapshot_url:
                try:
                    requests.put(
                        f"{SNAP_BASE_URL}/{slot_id}.json",
                        json={"url": live_snapshot_url, "ts": time.time()},
                        timeout=2
                    )
                except Exception as e:
                    print(f"📡 Snapshot history sync error: {e}")
            slot_index = (slot_index + 1) % 720
            last_snapshot_time = time.time()

        # C. Hardware Threshold Gating Trigger Evaluation Check
        if distance <= DISTANCE_THRESHOLD_CM:
            last_trigger_time = time.time()
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
                last_cnn_confidence = cnn_confidence
                cnn_verdict = LABELS[top_prediction_idx]

                # CNN confirms the ultrasonic trigger -> latch the flood and grab the image
                if cnn_verdict == "FLOOD ALERT ACTIVE":
                    flood_latched = True
                    last_flood_snapshot_url = upload_snapshot(raw_frame, folder="flood_alerts")
            else:
                flood_latched = True
                cnn_confidence = 100.0
                last_cnn_confidence = cnn_confidence
                print("Pre-Stage System: Automatically asserting FLOOD confirmation flag.")

            print(f"CNN Verdict Result: {'FLOOD ALERT ACTIVE' if flood_latched else 'Normal Conditions'} ({cnn_confidence:.1f}%)")

        # Auto-clear the latch once the ultrasonic has stopped breaching for the hold
        # window — so the status returns to SAFE instead of sticking on "flood".
        if flood_latched and (time.time() - last_trigger_time > FLOOD_HOLD_SECONDS):
            flood_latched       = False
            last_cnn_confidence = 0.0
            cnn_confidence      = 0.0

        # D. Derive status from the latch and reflect it on the LCD
        system_status = "FLOOD ALERT ACTIVE" if flood_latched else "Normal Conditions"
        lcd_display_text("!! FLOOD ALERT !!" if flood_latched else "STATUS: NORMAL", 1)

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
