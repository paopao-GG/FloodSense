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
const statusBanner       = document.getElementById("status-banner");
const statusText         = document.getElementById("status-text");
const lastUpdated        = document.getElementById("last-updated");
const waterLevel         = document.getElementById("water-level");
const temperature        = document.getElementById("temperature");
const humidity           = document.getElementById("humidity");
const cnnConfidence      = document.getElementById("cnn-confidence");
const latestSnapshot     = document.getElementById("latest-snapshot");
const noSnapshotMsg      = document.getElementById("no-snapshot-msg");
const snapshotHistory    = document.getElementById("snapshot-history");
const historyCount       = document.getElementById("history-count");
const lightbox           = document.getElementById("lightbox");
const lightboxImg        = document.getElementById("lightbox-img");

// Keep last 10 snapshot URLs (persisted across reloads)
const HISTORY_KEY = "flood_snapshot_history";
const MAX_HISTORY = 10;
let snapshotUrls = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");

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

function renderHistory() {
  snapshotHistory.innerHTML = "";
  historyCount.textContent = snapshotUrls.length > 0 ? `${snapshotUrls.length}` : "";
  snapshotUrls.forEach((url) => {
    const img = document.createElement("img");
    img.src = url;
    img.alt = "Snapshot";
    img.className = "gallery-thumb";
    img.onclick = () => openLightbox(url);
    snapshotHistory.appendChild(img);
  });
}

function updateSnapshot(url) {
  if (!url) return;
  if (latestSnapshot.src === url) return; // no change

  latestSnapshot.src = url;
  latestSnapshot.classList.remove("hidden");
  noSnapshotMsg.classList.add("hidden");
  latestSnapshot.onclick = () => openLightbox(url);

  // Prepend to history if new
  if (snapshotUrls[0] !== url) {
    snapshotUrls.unshift(url);
    if (snapshotUrls.length > MAX_HISTORY) snapshotUrls.pop();
    localStorage.setItem(HISTORY_KEY, JSON.stringify(snapshotUrls));
    renderHistory();
  }
}

function setStatus(statusStr) {
  const isFlood = statusStr?.includes("FLOOD");
  statusBanner.className = "status-banner " + (isFlood ? "alert" : "normal");
  statusText.textContent = isFlood ? "⚠ FLOOD ALERT ACTIVE" : "STATUS: NORMAL";
}

// ── Real-time listener ────────────────────────────────────────────────────────
onValue(
  ref(db, "flood_telemetry"),
  (snapshot) => {
    const data = snapshot.val();
    if (!data) return;

    setStatus(data.status);
    waterLevel.textContent    = data.water_depth_gap_cm != null ? data.water_depth_gap_cm.toFixed(1) : "—";
    temperature.textContent   = data.temperature_c      != null ? data.temperature_c                 : "—";
    humidity.textContent      = data.humidity_percent   != null ? data.humidity_percent               : "—";
    cnnConfidence.textContent = data.cnn_confidence     ?? "—";
    lastUpdated.textContent   = "Last updated: " + formatTimestamp(data.epoch_timestamp);

    if (data.snapshot_url) {
      updateSnapshot(data.snapshot_url);
    }
  },
  (error) => {
    statusText.textContent = "ERROR: " + error.code;
    console.error("Firebase error:", error.code, error.message);
  }
);

// Render any saved history on load
renderHistory();
