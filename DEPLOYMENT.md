# Flood Monitor — Deployment Guide

All services used here are **free tier only**. No credit card required.

---

## Overview of the stack

```
Raspberry Pi  ──►  Firebase RTDB (sensor data)  ──►  Vercel (flood-webapp/)
                ──►  Cloudinary (snapshots)      ──►  Vercel (flood-webapp/)
```

| Layer | Service | Free limit |
|-------|---------|-----------|
| Sensor backend | `Flood_system_final.py` on Raspberry Pi | — |
| Cloud database | Firebase Realtime Database (Spark plan) | 1 GB storage, 10 GB/month download |
| Image storage | Cloudinary | 25 GB storage, 25 GB/month bandwidth |
| Web dashboard | Vercel static hosting | Unlimited for static sites |

---

## Step 1 — Create a Firebase Project

1. Go to [https://console.firebase.google.com](https://console.firebase.google.com)
2. Click **Add project**
3. Enter a project name (e.g. `flood-monitor`) → disable Google Analytics → click **Create project**
4. Wait for it to finish, then click **Continue**

---

## Step 2 — Enable Realtime Database

1. In the left sidebar, click **Build → Realtime Database**
2. Click **Create Database**
3. Choose your nearest server location
4. Select **Start in test mode** → click **Enable**
5. Copy your database URL — it looks like:
   ```
   https://flood-monitor-xxxxx-default-rtdb.firebaseio.com
   ```

---

## Step 3 — Create a Cloudinary Account

1. Go to [https://cloudinary.com/users/register_free](https://cloudinary.com/users/register_free)
2. Sign up with your email — no credit card needed
3. After logging in, go to your **Dashboard**
4. At the top of the dashboard you will see three values — copy all three:

```
Cloud Name:  your-cloud-name
API Key:     123456789012345
API Secret:  AbCdEfGhIjKlMnOpQrStUvWxYz0
```

---

## Step 4 — Get the Firebase Web App Config (for Vercel)

1. In the Firebase Console, click the **gear icon → Project settings**
2. Scroll to **Your apps** → click the **`</>`** (Web) icon
3. Enter an app nickname (e.g. `flood-webapp`) — do NOT check Firebase Hosting → click **Register app**
4. Copy the config block shown:

```js
const firebaseConfig = {
  apiKey:            "AIzaSy...",
  authDomain:        "flood-monitor-xxxxx.firebaseapp.com",
  databaseURL:       "https://flood-monitor-xxxxx-default-rtdb.firebaseio.com",
  projectId:         "flood-monitor-xxxxx",
  storageBucket:     "flood-monitor-xxxxx.appspot.com",
  messagingSenderId: "123456789",
  appId:             "1:123456789:web:abcdef"
};
```

5. Paste these values into `flood-webapp/app.js`, replacing each `YOUR_*` placeholder
6. Click **Continue to console**

---

## Step 5 — Configure the Pi Code

Open `Flood_system_final.py` and update these values near the top:

```python
# Firebase RTDB URL (from Step 2)
WEB_URL = "https://flood-monitor-xxxxx-default-rtdb.firebaseio.com/flood_telemetry.json"

# Cloudinary credentials (from Step 3)
CLOUDINARY_CLOUD_NAME = "your-cloud-name"
CLOUDINARY_API_KEY    = "your-api-key"
CLOUDINARY_API_SECRET = "your-api-secret"
```

> **Security note:** Do not commit your Cloudinary API secret to GitHub. If you push the full project, add `Flood_system_final.py` to `.gitignore` or use environment variables.

---

## Step 6 — Enable I2C on the Pi (LCD)

If you haven't done this already:

```bash
sudo raspi-config
# Navigate to: Interface Options → I2C → Enable → Finish
sudo reboot
```

Confirm the LCD is detected after reboot:

```bash
i2cdetect -y 1
# You should see "27" in the grid (address 0x27)
```

---

## Step 7 — Install Dependencies on the Pi

SSH into your Raspberry Pi and run:

```bash
cd /home/ralphazanza/flood_project
source env/bin/activate
pip install cloudinary
```

Verify:

```bash
python -c "import cloudinary; print('cloudinary OK')"
```

---

## Step 8 — Test the Pi Backend

Run the main script:

```bash
cd /home/ralphazanza/flood_project
source env/bin/activate
python Flood_system_final.py
```

**Expected output (normal conditions):**
```
Powering up hardware peripherals...
Allocating memory arrays for Edge-AI TFLite engine...
🎥 Camera sensor matrix active and locked.
🚀 System active. Running monitoring routine loop...
Metrics -> Distance: 85.3cm | Temp: 28°C | Hum: 72%
```

**Verify data in Firebase:**
1. Go to **Firebase Console → Realtime Database**
2. A `flood_telemetry` node should appear within a few seconds:

```json
{
  "flood_telemetry": {
    "status": "Normal Conditions",
    "cnn_confidence": "0.0%",
    "water_depth_gap_cm": 85.3,
    "temperature_c": 28,
    "humidity_percent": 72,
    "epoch_timestamp": 1748476800.123
  }
}
```

**Test a snapshot upload:**

Bring your hand within 30 cm of the ultrasonic sensor. You should see:

```
⚠️ THRESHOLD BREACHED (22.4cm) -> Running CNN Verification...
📷 Snapshot uploaded: https://res.cloudinary.com/your-cloud-name/image/upload/...
📡 Firebase Cloud Updated! HTTP Status: 200
```

Verify in **Cloudinary Dashboard → Media Library** — a `flood_snapshots/` folder should contain the image.

---

## Step 9 — Configure the Webapp

Open `flood-webapp/app.js` and fill in the Firebase config values from Step 4:

```js
const firebaseConfig = {
  apiKey:            "AIzaSy...",
  authDomain:        "flood-monitor-xxxxx.firebaseapp.com",
  databaseURL:       "https://flood-monitor-xxxxx-default-rtdb.firebaseio.com",
  projectId:         "flood-monitor-xxxxx",
  storageBucket:     "flood-monitor-xxxxx.appspot.com",
  messagingSenderId: "123456789",
  appId:             "1:123456789:web:abcdef"
};
```

**Test locally before deploying:**

```bash
cd /home/ralphazanza/flood_project/flood-webapp
python3 -m http.server 8080
# Open http://localhost:8080 in a browser
```

The status banner should show live sensor values within a few seconds.

---

## Step 10 — Deploy to Vercel

### 10a — Push the webapp to GitHub

```bash
cd /home/ralphazanza/flood_project/flood-webapp
git init
git add .
git commit -m "Initial flood monitor webapp"
git remote add origin https://github.com/YOUR_USERNAME/flood-monitor-webapp.git
git push -u origin main
```

> Only push the `flood-webapp/` contents. The Pi project root (which has your credentials) should stay off GitHub.

### 10b — Connect to Vercel

1. Go to [https://vercel.com](https://vercel.com) → sign in with GitHub
2. Click **Add New → Project**
3. Import your `flood-monitor-webapp` repository
4. Leave all build settings as defaults (static site, no build command)
5. Click **Deploy**

Vercel gives you a URL like `https://flood-monitor-webapp.vercel.app`.

### 10c — Add a Custom Domain (optional)

1. In the Vercel project, click **Settings → Domains → Add Domain**
2. Enter your domain name and follow the DNS instructions
3. Vercel provisions SSL automatically

---

## Step 11 — Tighten Firebase Security Rules

Once everything is working, lock down your RTDB so only the Pi can write.

Go to **Firebase Console → Realtime Database → Rules** and set:

```json
{
  "rules": {
    "flood_telemetry": {
      ".read": true,
      ".write": false
    }
  }
}
```

This lets the webapp read data publicly but blocks writes from the browser. The Pi writes directly via the REST API using your `WEB_URL` which can be further secured with a Firebase secret if needed.

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| `Snapshot upload failed: Must supply api_key` | Cloudinary credentials not set | Check `CLOUDINARY_API_KEY` in `Flood_system_final.py` |
| `Snapshot upload failed: 401` | Wrong API secret | Re-copy `CLOUDINARY_API_SECRET` from the dashboard |
| Webapp shows "CONNECTING..." forever | Wrong `databaseURL` in `app.js` | Re-check config from Step 4 |
| Sensor values not updating | RTDB test mode expired (30 days) | Update RTDB rules as shown in Step 11 |
| Snapshots not appearing on webapp | Snapshot only uploads on threshold breach | Hold hand within 30 cm of sensor to trigger |
| LCD shows nothing | I2C not enabled or wrong address | Run `i2cdetect -y 1` and check for `27` in the grid |
| Script crashes on import | `cloudinary` not installed | Run `pip install cloudinary` inside the venv |

---

## Auto-start on Boot (optional)

To run the flood monitor automatically when the Pi powers on:

```bash
sudo nano /etc/systemd/system/flood-monitor.service
```

Paste:

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

Enable it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable flood-monitor
sudo systemctl start flood-monitor

# Check status
sudo systemctl status flood-monitor

# Stream live logs
journalctl -u flood-monitor -f
```
