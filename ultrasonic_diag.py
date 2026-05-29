import time, RPi.GPIO as GPIO
TRIG, ECHO = 23, 24
GPIO.setmode(GPIO.BCM); GPIO.setwarnings(True)
GPIO.setup(TRIG, GPIO.OUT); GPIO.setup(ECHO, GPIO.IN)
GPIO.output(TRIG, False); time.sleep(0.1)

hi = sum(GPIO.input(ECHO) for _ in range(1000))
print(f"Idle ECHO HIGH {hi}/1000 -> "
      f"{'STUCK HIGH' if hi>950 else 'STUCK LOW' if hi<50 else 'TOGGLING'}")

def ping(trig_us=10, timeout=0.06):
    GPIO.output(TRIG, False); time.sleep(0.05)
    GPIO.output(TRIG, True);  time.sleep(trig_us/1e6); GPIO.output(TRIG, False)
    t0 = time.time()
    while GPIO.input(ECHO) == 0:
        if time.time()-t0 > timeout: return ("NO_RISE", None)
    rise = time.time()
    while GPIO.input(ECHO) == 1:
        if time.time()-rise > timeout: return ("NO_FALL", None)
    return ("OK", round((time.time()-rise)*1e6*0.01715, 2))  # cm

for tw in (10, 20):
    print(f"\n--- trigger {tw}us ---")
    for _ in range(5):
        b, d = ping(trig_us=tw)
        print(f"  {b}" + (f"  -> {d} cm" if d is not None else "")); time.sleep(0.2)
GPIO.cleanup()
