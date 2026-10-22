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
import { getDatabase, ref, onValue, set, get } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-database.js";
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
const waterCanvas           = document.getElementById("water-chart");
const cnnCanvas             = document.getElementById("cnn-chart");
const viewTabs              = document.querySelectorAll(".view-tab");
const views                 = document.querySelectorAll(".view");
const exportBtn             = document.getElementById("export-btn");
const exportNote            = document.getElementById("export-note");

const SIX_HOURS = 6 * 3600;

// ── Chart setup ───────────────────────────────────────────────────────────────
const MAX_CHART_POINTS = 60;
const chartLabels  = [];
const tempData     = [];
const humidityData = [];
const waterData    = [];
const cnnData      = [];

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

const tempChart     = makeChart(tempCanvas,     "Temperature °C",   "#f59e0b", 15, 45);
const humidityChart = makeChart(humidityCanvas, "Humidity %",       "#6366f1",  0, 100);
const waterChart    = makeChart(waterCanvas,    "Water Level cm",   "#38bdf8",  0, 60);
const cnnChart      = makeChart(cnnCanvas,      "CNN Confidence %", "#c084fc",  0, 100);
const allCharts     = [tempChart, humidityChart, waterChart, cnnChart];

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

function pushChartPoint(ts, temp, hum, water, cnn) {
  const timeLabel = ts
    ? new Date(ts * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
    : "—";

  if (chartLabels.length >= MAX_CHART_POINTS) {
    chartLabels.shift();
    tempData.shift();
    humidityData.shift();
    waterData.shift();
    cnnData.shift();
  }
  chartLabels.push(timeLabel);

  // null renders as a gap in the line rather than a zero/sentinel spike
  tempData.push(temp !== 0 ? temp : null);
  humidityData.push(hum !== 0 ? hum : null);
  waterData.push(water != null && water < 400 ? water : null);  // 999 = ultrasonic timeout
  cnnData.push(cnn ? cnn : null);                                // 0% = no detection ran

  tempChart.data.datasets[0].data     = [...tempData];
  humidityChart.data.datasets[0].data = [...humidityData];
  waterChart.data.datasets[0].data    = [...waterData];
  cnnChart.data.datasets[0].data      = [...cnnData];
  tempChart.update("none");
  humidityChart.update("none");
  waterChart.update("none");
  cnnChart.update("none");
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

// ── Reading log (one row per minute, shared by every open dashboard) ─────────
// ponytail: browsers do the logging because the Pi only overwrites the latest
// reading, so there are gaps while no dashboard is open. For 24/7 history, have
// the Pi PUT the same readings/<minute> key and delete this.
let lastLoggedMinute = 0;

function logReading(data) {
  // Keyed by the Pi's timestamp: tabs open at the same time write the same
  // slot, and a stale reading never adds a new row.
  const minute = Math.floor(data.epoch_timestamp / 60);
  if (!minute || minute === lastLoggedMinute) return;
  lastLoggedMinute = minute;
  set(ref(db, `readings/${minute}`), {
    ts:       data.epoch_timestamp,
    status:   data.status             ?? null,
    water_cm: data.water_depth_gap_cm ?? null,
    temp_c:   data.temperature_c      ?? null,
    humidity: data.humidity_percent   ?? null,
    cnn:      data.cnn_confidence     ?? null,
  }).catch((e) => console.error("Reading log failed:", e.code, e.message));
}

// ── Real-time listener ────────────────────────────────────────────────────────
onValue(
  ref(db, "flood_telemetry"),
  (snapshot) => {
    const data = snapshot.val();
    if (!data) return;

    setStatus(data.status);
    markFresh();
    logReading(data);
    if (data.location) locationEl.textContent = data.location;
    waterLevel.textContent    = data.water_depth_gap_cm != null ? data.water_depth_gap_cm.toFixed(1) : "—";
    temperature.textContent   = data.temperature_c      != null ? data.temperature_c                 : "—";
    humidity.textContent      = data.humidity_percent   != null ? data.humidity_percent               : "—";
    cnnConfidence.textContent = data.cnn_confidence     ?? "—";
    lastUpdated.textContent   = "Last updated " + formatTimestamp(data.epoch_timestamp);

    updateLiveSnapshot(data.live_snapshot_url);
    updateFloodSnapshot(data.flood_snapshot_url);
    pushChartPoint(
      data.epoch_timestamp,
      data.temperature_c ?? 0,
      data.humidity_percent ?? 0,
      data.water_depth_gap_cm ?? null,
      parseFloat(data.cnn_confidence) || 0
    );
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

// ── Export XLSX ──────────────────────────────────────────────────────────────
async function exportReadings() {
  exportBtn.disabled = true;
  exportBtn.textContent = "Exporting…";
  try {
    // ponytail: pulls the whole node (~1,440 rows/day); add an
    // orderByKey().startAt() date range when exports get slow.
    const snap = await get(ref(db, "readings"));
    const readings = Object.values(snap.val() || {}).sort((a, b) => a.ts - b.ts);
    if (!readings.length) {
      exportNote.textContent = "No readings saved yet. Keep the dashboard open for a minute.";
      return;
    }

    // Loaded on click only: SheetJS is ~1 MB and most visitors never export.
    const XLSX = await import("https://cdn.sheetjs.com/xlsx-0.20.3/package/xlsx.mjs");
    const rows = readings.map((r) => ({
      "Time":             new Date(r.ts * 1000),
      "Status":           r.status,
      "Water Level (cm)": r.water_cm,
      "Temperature (°C)": r.temp_c,
      "Humidity (%)":     r.humidity,
      "CNN Confidence (%)": r.cnn == null ? null : parseFloat(r.cnn),  // Pi sends "97.5%"
    }));
    const ws = XLSX.utils.json_to_sheet(rows, { dateNF: "yyyy-mm-dd hh:mm:ss" });
    ws["!cols"] = [{ wch: 20 }, { wch: 20 }, { wch: 17 }, { wch: 17 }, { wch: 13 }, { wch: 15 }];
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Readings");
    XLSX.writeFile(wb, `floodsense_readings_${new Date().toLocaleDateString("en-CA")}.xlsx`);
    exportNote.textContent = `Exported ${readings.length} readings.`;
  } catch (e) {
    console.error("Export failed:", e);
    exportNote.textContent = "Export failed. See the browser console.";
  } finally {
    exportBtn.disabled = false;
    exportBtn.textContent = "Export XLSX";
  }
}
exportBtn.addEventListener("click", exportReadings);

// ── View switcher (Dashboard / Data Analysis / Rationale) ──────────────────────
const VIEWS = ["dashboard", "analysis", "rationale"];

function switchView(name) {
  if (!VIEWS.includes(name)) name = "dashboard";
  views.forEach(v => v.classList.toggle("active", v.id === "view-" + name));
  viewTabs.forEach(t => t.classList.toggle("active", t.dataset.view === name));
  if (location.hash.slice(1) !== name) location.hash = name;  // deep-link / survive refresh
  // Chart.js canvases laid out at 0px while hidden — recompute once visible.
  if (name === "analysis") {
    requestAnimationFrame(() => allCharts.forEach(c => c.resize()));
  }
}
viewTabs.forEach(tab => tab.addEventListener("click", () => switchView(tab.dataset.view)));
window.addEventListener("hashchange", () => switchView(location.hash.slice(1)));
switchView(location.hash.slice(1) || "dashboard");

// ── Footer year ──────────────────────────────────────────────────────────────
const footerYear = document.getElementById("footer-year");
if (footerYear) footerYear.textContent = new Date().getFullYear();
