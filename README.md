# Flood Sense

**Web-Based: Solar-Powered IoT Flood Warning Device Integrating CNN Image Processing**

Department of Electrical Engineering · College of Engineering · Bicol University
AZANZA, RAP • NAZ, KP • ONOYA, MLC • OPEDA, RMB

A Raspberry Pi reads an ultrasonic water-level sensor and a DHT11 temperature/humidity
sensor. When the water rises past a threshold, a quantized CNN classifies a camera
frame as flood / not-flood. Readings and snapshots are pushed to the cloud and shown
on a live public dashboard.

---

## Architecture

```
┌──────────────────────────┐        ┌────────────────────────┐       ┌──────────────────────┐
│   Raspberry Pi (server)  │        │        Cloud           │       │   Vercel (website)   │
│  Flood_system_final.py   │──────► │  Firebase RTDB         │ ────► │  flood-webapp/       │
│  • ultrasonic + DHT11     │ data  │   (sensor telemetry)   │       │  live dashboard      │
│  • TFLite CNN on camera   │       │  Cloudinary            │       │  charts + snapshots  │
│  • 20x4 I2C LCD           │──────►│   (snapshot images)    │ ────► │                      │
│  runs as systemd service  │ images└────────────────────────┘       └──────────────────────┘
└──────────────────────────┘
```

- **Pi backend** → see [docs/RASPBERRY_PI.md](docs/RASPBERRY_PI.md)
- **Web dashboard** → see [docs/VERCEL.md](docs/VERCEL.md)
- **First-time full setup** → see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **What changed over time** → see [docs/CHANGELOG.md](docs/CHANGELOG.md)

---

## Documentation

| Doc | What it covers |
|-----|----------------|
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | Commit-by-commit review of what was added to the code. |
| [docs/RASPBERRY_PI.md](docs/RASPBERRY_PI.md) | **Restarting the Pi server after editing the `.py` file.** |
| [docs/VERCEL.md](docs/VERCEL.md) | **Making changes to the Vercel webapp.** |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | First-time setup: Firebase, Cloudinary, Vercel, I2C, dependencies. |
| [docs/webapp.md](docs/webapp.md) | Original webapp requirements notes. |
| [docs/changes.md](docs/changes.md) | Original change-request notes. |

---

## Directory layout

```
flood_project/
├── README.md                     ← you are here
├── docs/                         ← all documentation (safe to edit/move freely)
│   ├── CHANGELOG.md
│   ├── RASPBERRY_PI.md
│   ├── VERCEL.md
│   ├── DEPLOYMENT.md
│   ├── webapp.md
│   └── changes.md
│
├── Flood_system_final.py         ★ Pi production server (run by systemd)
├── flood_model_quantized.tflite  ★ CNN model weights (loaded by relative path)
├── env/                          ★ Python virtualenv (referenced by systemd)
├── flood-webapp/                 ★ the website Vercel deploys
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   └── img/                      (logos + favicon the site serves)
│
├── Flood_predict.py              dev: offline single-image CNN test
├── Flood_predict_Camon.py        dev: live-camera CNN test
├── camera_test.py                dev: camera hardware check
├── ultrasonic_diag.py            dev: ultrasonic sensor diagnostic
├── test_scene.jpg                test image for Flood_predict.py
├── camera_test_snapshot.jpg      output of camera_test.py
├── img/                          original/source logos (site uses flood-webapp/img/)
└── .env                          local secrets/notes (gitignored — never commit)
```

`★ = server-critical, do not move (see below).`

---

## ⚠️ Do not move these — server-critical paths

The documentation was reorganized into `docs/`. **The functional files were left in
place on purpose** because two live servers depend on their exact location:

**1. Raspberry Pi service** — `/etc/systemd/system/flood-monitor.service` is wired to:
```ini
WorkingDirectory=/home/ralphazanza/flood_project
ExecStart=/home/ralphazanza/flood_project/env/bin/python Flood_system_final.py
```
So **`Flood_system_final.py`**, the **`env/`** virtualenv, and
**`flood_model_quantized.tflite`** (loaded via the relative string
`"flood_model_quantized.tflite"`) must stay in the project root. Moving any of them
stops the Pi from booting the monitor.

**2. Vercel website** — Vercel's **Root Directory is `flood-webapp`**. Renaming or
moving **`flood-webapp/`** (or rearranging the files inside it, which reference
`style.css` / `app.js` / `img/*` by relative path) breaks the deployed site.

If you ever *do* need to move one of these, update the dependent config in the same
change: the systemd unit for the Pi (`sudo systemctl daemon-reload` after), and the
Root Directory in Vercel → Settings → Build & Deployment.

The dev/test scripts (`Flood_predict*.py`, `camera_test.py`, `ultrasonic_diag.py`)
also load the model and test images by relative path, so run them from the project
root.

---

## Quick reference

```bash
# Restart the Pi server after editing Flood_system_final.py
sudo systemctl restart flood-monitor
journalctl -u flood-monitor -f

# Push a website change (Vercel auto-deploys from flood-webapp/)
git add flood-webapp/ && git commit -m "update site" && git push origin main
```
