# Changelog — What Was Added to the Code

A commit-by-commit review of how Flood Sense evolved, newest first. Hashes match
`git log`. This is a plain-English summary of *what each change added* — see the
commit diffs for line-level detail.

---

## `e98067f` — Nav tabs, data-analysis charts, rationale page, flood-status latch
**2026-05-30**

The biggest UI + logic release.

**Web dashboard (`flood-webapp/`)**
- Added a top **navigation bar** with three views: **Dashboard**, **Data Analysis**,
  and **Rationale** (`index.html`, `app.js` `switchView()`). The active view is
  stored in the URL hash so it survives a refresh and can be deep-linked.
- **Data Analysis** view now holds *all four* trend charts (Temperature, Humidity,
  Water Level, CNN Confidence) — moved out of the main dashboard so the dashboard
  stays focused on live readings.
- Added a **Rationale** page describing the project.
- New darker-blue header styling to complement the logos (`style.css`).

**Pi backend (`Flood_system_final.py`)**
- Added a **flood-status latch** (`FLOOD_HOLD_SECONDS = 30`). Once the CNN confirms a
  flood, the status holds `FLOOD ALERT ACTIVE` and only resets to safe after the
  ultrasonic sensor stops breaching the threshold for 30 s. This stops the status
  from flapping every cycle and from getting permanently stuck on "flood" after the
  water recedes. (Directly implements the request in [changes.md](changes.md).)

---

## `46dfe0a` — UI color improvements
**2026-05-29**
- Reworked the dashboard color palette (`style.css` only).

## `067389e` — UI improvements
**2026-05-29**
- Large visual overhaul of `index.html` / `style.css` / `app.js`.
- Added project/department logos: `img/iiee.png`, `img/buceng.png` (and the
  `flood-webapp/img/` copies the site actually serves).
- Removed the old `webapp.md` notes from the repo root.

## `32e5f9f` — Live camera feed → "Latest Snapshot"
**2026-05-29**
- Reframed the live camera area as a **"Latest Snapshot"** panel that refreshes from
  the periodic 30-second upload, with cache-busting so the browser re-fetches the
  overwritten Cloudinary slot.

## `9ca0e6c` — Authors & titles
**2026-05-29**
- Added the author list (`AZANZA, RAP • NAZ, KP • ONOYA, MLC • OPEDA, RMB`) and the
  research title to the footer/header.

## `cc00882` — Temperature/humidity graphs + reading normalization
**2026-05-29**
- **Web:** added live Chart.js trend graphs for temperature and humidity.
- **Pi:** added **DHT11 noise filtering** — EMA smoothing (`EMA_ALPHA = 0.3`) plus a
  "hold last valid reading" fallback so a failed/zeroed read doesn't spike the graph.

## `9d2dcb7` — 6-hour snapshot history with timestamps
**2026-05-29**
- **Pi:** writes each 30-second snapshot to a rolling slot (`slot_000`–`slot_719`,
  one per 30 s = 6 hours) under the Firebase `snapshots` node and to a fixed
  Cloudinary slot per index, with a timestamp.
- **Web:** added the "Last 6 Hours" gallery that reads the `snapshots` node, filters
  to the last 6 h, and renders timestamped thumbnails.

## `f99644c` — Camera & location working in the webapp
**2026-05-29**
- **Pi:** snapshots upload to Cloudinary and the `location` field is sent in the
  Firebase telemetry payload.
- **Web:** displays the camera snapshot and the device location.

## `0ed0073` — Initial webapp integration
**2026-05-29**
- First version of `flood-webapp/` (`index.html`, `app.js`, `style.css`) reading
  **water level, temperature, humidity** live from Firebase.
- Added the original **[DEPLOYMENT.md](DEPLOYMENT.md)** guide.
- Wired `Flood_system_final.py` to push telemetry to Firebase.
- Known issues noted at the time: water-level sensor reading and location.

## `a79aae7` — Initial commit: FloodSense monitoring system
**2026-05-28**
- First version of the Raspberry Pi system: `Flood_system_final.py`.
- Helper / test scripts: `Flood_predict.py` (offline single-image CNN test),
  `Flood_predict_Camon.py` (live camera CNN test), `camera_test.py` (camera check).
- The quantized CNN model `flood_model_quantized.tflite` and test images.

---

## Untracked / in-progress

- `ultrasonic_diag.py` — a standalone diagnostic that pings the HC-SR04 ultrasonic
  sensor and reports whether the ECHO line is stuck high/low or toggling. Useful when
  the water-level reading returns `999.0` (sensor-not-responding sentinel). Not yet
  committed.
