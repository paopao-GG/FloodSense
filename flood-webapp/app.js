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
import Chart                          from "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/auto/+esm";

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
const tempCanvas            = document.getElementById("temp-chart");
const humidityCanvas        = document.getElementById("humidity-chart");

const SIX_HOURS = 6 * 3600;

// ── Chart setup ───────────────────────────────────────────────────────────────
const MAX_CHART_POINTS = 60;
const chartLabels  = [];
const tempData     = [];
const humidityData = [];

function hexToRgba(hex, alpha) {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

function makeChart(canvas, label, color, suggestedMin, suggestedMax) {
  const ctx = canvas.getContext("2d");
  const gradient = ctx.createLinearGradient(0, 0, 0, 180);
  gradient.addColorStop(0, hexToRgba(color, 0.35));
  gradient.addColorStop(1, hexToRgba(color, 0));

  return new Chart(canvas, {
    type: "line",
    data: {
      labels: chartLabels,
      datasets: [{
        label,
        data: [],
        borderColor: color,
        backgroundColor: gradient,
        borderWidth: 2.5,
        pointRadius: 0,
        pointHoverRadius: 4,
        pointHoverBackgroundColor: color,
        pointHoverBorderColor: "#0a0c14",
        pointHoverBorderWidth: 2,
        tension: 0.35,
        fill: true,
        spanGaps: true,
      }]
    },
    options: {
      animation: false,
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "rgba(15,18,32,0.95)",
          borderColor: "#2a3050",
          borderWidth: 1,
          titleColor: "#eef0fb",
          bodyColor: "#bcc1e0",
          padding: 10,
          cornerRadius: 8,
          displayColors: false,
        }
      },
      scales: {
        x: {
          ticks: { color: "#7b82a8", maxTicksLimit: 6, font: { size: 10, family: "Inter" } },
          grid:  { color: "rgba(42,48,80,0.5)", drawBorder: false },
        },
        y: {
          suggestedMin,
          suggestedMax,
          ticks: { color: "#7b82a8", font: { size: 10, family: "Inter" } },
          grid:  { color: "rgba(42,48,80,0.5)", drawBorder: false },
        }
      }
    }
  });
}

const tempChart     = makeChart(tempCanvas,     "Temperature °C", "#f59e0b", 15, 45);
const humidityChart = makeChart(humidityCanvas, "Humidity %",     "#6366f1",  0, 100);

// ── Helpers ───────────────────────────────────────────────────────────────────
async function downloadImage(url) {
  try {
    const res  = await fetch(url);
    const blob = await res.blob();
    const a    = document.createElement("a");
    a.href     = URL.createObjectURL(blob);
    a.download = "floodsense_" + Date.now() + ".jpg";
    a.click();
    URL.revokeObjectURL(a.href);
  } catch (e) {
    console.error("Download failed:", e);
  }
}

window.downloadLightboxImage = function () {
  if (lightboxImg.src) downloadImage(lightboxImg.src);
};

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

    const dlBtn = document.createElement("button");
    dlBtn.className   = "thumb-dl";
    dlBtn.title       = "Download";
    dlBtn.textContent = "⬇";
    dlBtn.onclick = (e) => { e.stopPropagation(); downloadImage(url); };

    wrapper.appendChild(img);
    wrapper.appendChild(label);
    wrapper.appendChild(dlBtn);
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

function pushChartPoint(ts, temp, hum) {
  const timeLabel = ts
    ? new Date(ts * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
    : "—";

  if (chartLabels.length >= MAX_CHART_POINTS) {
    chartLabels.shift();
    tempData.shift();
    humidityData.shift();
  }
  chartLabels.push(timeLabel);

  // null renders as a gap in the line rather than a zero spike
  tempData.push(temp !== 0 ? temp : null);
  humidityData.push(hum !== 0 ? hum : null);

  tempChart.data.datasets[0].data     = [...tempData];
  humidityChart.data.datasets[0].data = [...humidityData];
  tempChart.update("none");
  humidityChart.update("none");
}

let lastFloodState = "safe";

function setStatus(statusStr) {
  const isFlood = statusStr?.includes("FLOOD");
  lastFloodState = isFlood ? "alert" : "normal";

  statusBanner.className = "status-banner " + lastFloodState;
  statusText.textContent = isFlood ? "⚠ FLOOD DETECTED" : "SAFE";

  floodStatusChip.textContent = isFlood ? "FLOOD DETECTED" : "SAFE";
  floodStatusChip.className   = "flood-chip " + (isFlood ? "flood" : "safe");
  floodSection.className      = "flood-section " + (isFlood ? "active" : "");
}

// ── Stale-data detector ──────────────────────────────────────────────────────
// If no Firebase update for >60s, dim the status pill to "stale" so operators
// know they're looking at frozen data.
const STALE_AFTER_MS = 60_000;
let lastUpdateMs = 0;
let staleCheckTimer = null;

function markFresh() {
  lastUpdateMs = Date.now();
  if (statusBanner.classList.contains("stale")) {
    statusBanner.classList.remove("stale");
    statusBanner.classList.add(lastFloodState);
    statusText.textContent = lastFloodState === "alert" ? "⚠ FLOOD DETECTED" : "SAFE";
  }
}

function checkStale() {
  if (!lastUpdateMs) return;
  if (Date.now() - lastUpdateMs > STALE_AFTER_MS && !statusBanner.classList.contains("stale")) {
    statusBanner.classList.remove("normal", "alert");
    statusBanner.classList.add("stale");
    statusText.textContent = "STALE · NO RECENT DATA";
  }
}

staleCheckTimer = setInterval(checkStale, 10_000);

// ── Real-time listener ────────────────────────────────────────────────────────
onValue(
  ref(db, "flood_telemetry"),
  (snapshot) => {
    const data = snapshot.val();
    if (!data) return;

    setStatus(data.status);
    markFresh();
    if (data.location) locationEl.textContent = data.location;
    waterLevel.textContent    = data.water_depth_gap_cm != null ? data.water_depth_gap_cm.toFixed(1) : "—";
    temperature.textContent   = data.temperature_c      != null ? data.temperature_c                 : "—";
    humidity.textContent      = data.humidity_percent   != null ? data.humidity_percent               : "—";
    cnnConfidence.textContent = data.cnn_confidence     ?? "—";
    lastUpdated.textContent   = "Last updated " + formatTimestamp(data.epoch_timestamp);

    updateLiveSnapshot(data.live_snapshot_url);
    updateFloodSnapshot(data.flood_snapshot_url);
    pushChartPoint(data.epoch_timestamp, data.temperature_c ?? 0, data.humidity_percent ?? 0);
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

// ── Footer year ──────────────────────────────────────────────────────────────
const footerYear = document.getElementById("footer-year");
if (footerYear) footerYear.textContent = new Date().getFullYear();
