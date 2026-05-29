# Raspberry Pi Server — Restarting After You Edit the Code

The Pi backend is `Flood_system_final.py`. It runs as a **systemd service** named
`flood-monitor`, which is set to **start on boot** and **auto-restart on crash**.

> ⚠️ **Do not move these files.** The service is hard-wired to these paths:
> ```ini
> WorkingDirectory=/home/ralphazanza/flood_project
> ExecStart=/home/ralphazanza/flood_project/env/bin/python Flood_system_final.py
> ```
> So `Flood_system_final.py`, the `env/` virtualenv, and
> `flood_model_quantized.tflite` (loaded by the relative path `"flood_model_quantized.tflite"`)
> **must stay in the project root**. Moving any of them breaks the server. See the
> root [README](../README.md#do-not-move-these--server-critical-paths).

---

## TL;DR — after editing `Flood_system_final.py`

```bash
sudo systemctl restart flood-monitor
```

That's the whole thing. systemd re-launches the script with your changes. To watch it
come back up:

```bash
journalctl -u flood-monitor -f
```

(Press `Ctrl+C` to stop watching the logs — that does **not** stop the service.)

---

## The full restart workflow

```bash
# 1. (Optional) edit on the Pi, or pull your latest changes
cd /home/ralphazanza/flood_project
git pull            # only if you push edits from elsewhere

# 2. Restart the service so the new code is loaded
sudo systemctl restart flood-monitor

# 3. Confirm it's running and watch live output
sudo systemctl status flood-monitor      # should say "active (running)"
journalctl -u flood-monitor -f           # live logs; Ctrl+C to exit
```

A healthy start looks like:

```
Powering up hardware peripherals...
Allocating memory arrays for Edge-AI TFLite engine...
🎥 Camera sensor matrix active and locked.
🚀 System active. Running monitoring routine loop...
Metrics -> Distance: 85.3cm | Temp: 28.0°C | Hum: 72.0%
📡 Firebase Cloud Updated! HTTP Status: 200
```

---

## All the service commands you need

| Goal | Command |
|------|---------|
| Restart after a code change | `sudo systemctl restart flood-monitor` |
| Stop it (e.g. to run the script by hand) | `sudo systemctl stop flood-monitor` |
| Start it again | `sudo systemctl start flood-monitor` |
| Check if it's running | `sudo systemctl status flood-monitor` |
| Live logs | `journalctl -u flood-monitor -f` |
| Last 100 log lines | `journalctl -u flood-monitor -n 100` |
| Run on every boot | `sudo systemctl enable flood-monitor` |
| Don't run on boot | `sudo systemctl disable flood-monitor` |

> **Note:** Because the service has `Restart=always`, you **cannot** stop the script
> just by killing it or pressing `Ctrl+C` — systemd relaunches it within 5 seconds.
> Use `sudo systemctl stop flood-monitor` to actually stop it.

---

## Editing the service definition itself

You only need this if you change a *path* or an *environment variable* — not for
ordinary code edits.

```bash
sudo nano /etc/systemd/system/flood-monitor.service
```

After **any** edit to that file, reload systemd's view of it before restarting:

```bash
sudo systemctl daemon-reload
sudo systemctl restart flood-monitor
```

Current contents (for reference):

```ini
[Unit]
Description=Flood Monitor
After=network.target

[Service]
User=ralphazanza
WorkingDirectory=/home/ralphazanza/flood_project
ExecStart=/home/ralphazanza/flood_project/env/bin/python Flood_system_final.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## Running it manually instead (for debugging)

To watch the script in your own terminal — handy when testing a tricky change — stop
the service first so two copies don't fight over the GPIO pins and camera:

```bash
sudo systemctl stop flood-monitor          # release the hardware
cd /home/ralphazanza/flood_project
source env/bin/activate
python Flood_system_final.py               # Ctrl+C to quit
```

When you're done debugging, hand control back to the service:

```bash
deactivate
sudo systemctl start flood-monitor
```

> Run from the project root (`/home/ralphazanza/flood_project`) so the relative
> `flood_model_quantized.tflite` path resolves. The same applies to the helper
> scripts (`Flood_predict.py`, `Flood_predict_Camon.py`, `camera_test.py`,
> `ultrasonic_diag.py`) — always launch them from the project root.

---

## If you change a config value (Firebase / Cloudinary / pins)

Those constants live near the top of `Flood_system_final.py`
(`FIREBASE_BASE`, `CLOUDINARY_*`, `TRIG_PIN`, `ECHO_PIN`, `DISTANCE_THRESHOLD_CM`,
`CAMERA_AVAILABLE`, …). They're read **once at startup**, so after editing them you
must restart the service for the change to take effect:

```bash
sudo systemctl restart flood-monitor
```

If you change the **Firebase database URL** here, change it in
[`flood-webapp/app.js`](../flood-webapp/app.js) too, or the Pi and the website will be
talking to different databases.

---

## Quick troubleshooting

| Symptom | Check |
|---------|-------|
| Status stuck on `activating` / keeps restarting | `journalctl -u flood-monitor -n 50` — usually a Python error or missing hardware. |
| `Missing custom model weights file` | `flood_model_quantized.tflite` was moved out of the project root — put it back. |
| Water level always `999.0` | Ultrasonic sensor not responding. Stop the service and run `python ultrasonic_diag.py` from the project root. |
| No data on the website | Confirm `📡 Firebase Cloud Updated! HTTP Status: 200` in the logs, and that the Pi has internet. |
| `ModuleNotFoundError` | The venv changed. Re-activate `env/` and `pip install` the missing package, then restart. |

See [DEPLOYMENT.md](DEPLOYMENT.md) for first-time setup (I2C, dependencies, Firebase,
Cloudinary).
