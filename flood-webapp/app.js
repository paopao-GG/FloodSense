// ─────────────────────────────────────────────────────────────────────────────
// Firebase config — fill in your project values from:
// Firebase Console → Project Settings → General → Your apps → SDK setup
// ─────────────────────────────────────────────────────────────────────────────
const firebaseConfig = {
  apiKey:            "AIzaSyAsQhGqrQjEhd3D0KiPzLgUE-jpju28Lio",
  authDomain:        "floodsense-ffce3.firebaseapp.com",
  databaseURL:       "https://floodsense-ffce3-default-rtdb.asia-southeast1.firebasedatabase.app",
  projectId:         "floodsense-ffce3",
  storageBucket:     "floodsense-ffce3.firebasestorage.app",
  messagingSenderId: "233538926218",
  appId:             "1:233538926218:web:ee7c842f1f534cb3f01f73",
};

import { initializeApp }              from "https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js";
import { getDatabase, ref, onValue }  from "https://www.gstatic.com/firebasejs/10.12.0/firebase-database.js";

const app = initializeApp(firebaseConfig);
const db  = getDatabase(app);

// ── DOM refs ──────────────────────────────────────────────────────────────────
const statusBanner          = document.getElementById("status-banner");
const statusText            = document.getElementById("status-text");
const locationEl            = document.getElementById("location");
const lastUpdated           = document.getElementById("last-updated");
const waterLevel            = document.getElementById("water-level");
const temperature           = document.getElementById("temperature");
const humidity              = document.getElementById("humidity");
const cnnConfidence         = document.getElementById("cnn-confidence");
const liveSnapshot          = document.getElementById("live-snapshot");
const noLiveMsg             = document.getElementById("no-live-msg");
const snapshotHistory       = document.getElementById("snapshot-history");
const historyCount          = document.getElementById("history-count");
const floodSection          = document.getElementById("flood-section");
const floodStatusChip       = document.getElementById("flood-status-chip");
const floodSnapshot         = document.getElementById("flood-snapshot");
const noFloodMsg            = document.getElementById("no-flood-msg");
const lightbox              = document.getElementById("lightbox");
const lightboxImg           = document.getElementById("lightbox-img");

const SIX_HOURS = 6 * 3600;

// ── Helpers ───────────────────────────────────────────────────────────────────
function formatTimestamp(epoch) {
  if (!epoch) return "—";
  return new Date(epoch * 1000).toLocaleString();
}

function openLightbox(src) {
  lightboxImg.src = src;
  lightbox.classList.remove("hidden");
}

window.closeLightbox = function () {
  lightbox.classList.add("hidden");
  lightboxImg.src = "";
};

function renderHistory(entries) {
  snapshotHistory.innerHTML = "";
  historyCount.textContent = entries.length > 0 ? `${entries.length}` : "";
  entries.forEach(({ url, ts }) => {
    const wrapper = document.createElement("div");
    wrapper.className = "thumb-wrapper";

    const img = document.createElement("img");
    img.src = url;
    img.alt = "Snapshot";
    img.className = "gallery-thumb";
    img.onclick = () => openLightbox(url);

    const label = document.createElement("span");
    label.className = "thumb-time";
    label.textContent = new Date(ts * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    wrapper.appendChild(img);
    wrapper.appendChild(label);
    snapshotHistory.appendChild(wrapper);
  });
}

function updateLiveSnapshot(url) {
  if (!url) return;
  // Append cache-bust so the browser re-fetches the overwritten Cloudinary slot
  const busted = url.includes("?") ? url : url + "?t=" + Date.now();
  liveSnapshot.src = busted;
  liveSnapshot.classList.remove("hidden");
  noLiveMsg.classList.add("hidden");
  liveSnapshot.onclick = () => openLightbox(url);
}

function updateFloodSnapshot(url) {
  if (!url || floodSnapshot.src === url) return;
  floodSnapshot.src = url;
  floodSnapshot.classList.remove("hidden");
  noFloodMsg.classList.add("hidden");
  floodSnapshot.onclick = () => openLightbox(url);
}

function setStatus(statusStr) {
  const isFlood = statusStr?.includes("FLOOD");

  // Main status banner
  statusBanner.className = "status-banner " + (isFlood ? "alert" : "normal");
  statusText.textContent = isFlood ? "⚠ FLOOD DETECTED" : "SAFE";

  // Flood section chip + border
  floodStatusChip.textContent = isFlood ? "FLOOD DETECTED" : "SAFE";
  floodStatusChip.className   = "flood-chip " + (isFlood ? "flood" : "safe");
  floodSection.className      = "flood-section " + (isFlood ? "active" : "");
}

// ── Real-time listener ────────────────────────────────────────────────────────
onValue(
  ref(db, "flood_telemetry"),
  (snapshot) => {
    const data = snapshot.val();
    if (!data) return;

    setStatus(data.status);
    if (data.location) locationEl.textContent = data.location;
    waterLevel.textContent    = data.water_depth_gap_cm != null ? data.water_depth_gap_cm.toFixed(1) : "—";
    temperature.textContent   = data.temperature_c      != null ? data.temperature_c                 : "—";
    humidity.textContent      = data.humidity_percent   != null ? data.humidity_percent               : "—";
    cnnConfidence.textContent = data.cnn_confidence     ?? "—";
    lastUpdated.textContent   = "Last updated: " + formatTimestamp(data.epoch_timestamp);

    updateLiveSnapshot(data.live_snapshot_url);
    updateFloodSnapshot(data.flood_snapshot_url);
  },
  (error) => {
    statusText.textContent = "ERROR: " + error.code;
    console.error("Firebase error:", error.code, error.message);
  }
);

// ── Snapshot history listener (separate node, 6-hour rolling window) ─────────
onValue(ref(db, "snapshots"), (snap) => {
  const data = snap.val();
  if (!data) return;
  const cutoff = Date.now() / 1000 - SIX_HOURS;
  const entries = Object.values(data)
    .filter(e => e && e.ts > cutoff)
    .sort((a, b) => b.ts - a.ts);
  renderHistory(entries);
});
