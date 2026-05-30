/**
 * app.js — Smart Traffic System
 * Interactive Leaflet map picker + API calls
 */

const API_BASE = "";

// ── State ─────────────────────────────────────────────────────────
let pickerMap    = null;
let originMarker = null;
let destMarker   = null;
let currentMode  = "origin";   // "origin" or "destination"
let originData   = null;       // {lat, lon, name}
let destData     = null;

// All known nodes from backend
let knownNodes   = {};

// ── Icons ──────────────────────────────────────────────────────────
const ORIGIN_ICON = L.divIcon({
  html: `<div style="background:#c0506a;color:white;width:32px;height:32px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);border:2px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center">
           <span style="transform:rotate(45deg);font-size:14px">+</span></div>`,
  iconSize: [32, 32], iconAnchor: [16, 32], className: ""
});

const DEST_ICON = L.divIcon({
  html: `<div style="background:#e09060;color:white;width:32px;height:32px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);border:2px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center">
           <span style="transform:rotate(45deg);font-size:12px">⚠</span></div>`,
  iconSize: [32, 32], iconAnchor: [16, 32], className: ""
});

const NODE_ICON = L.divIcon({
  html: `<div style="background:#8076a3;width:10px;height:10px;border-radius:50%;border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,0.2)"></div>`,
  iconSize: [10, 10], iconAnchor: [5, 5], className: ""
});

const HOSPITAL_ICON = L.divIcon({
  html: `<div style="background:#c0506a;color:white;width:18px;height:18px;border-radius:50%;border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,0.25);display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:bold">+</div>`,
  iconSize: [18, 18], iconAnchor: [9, 9], className: ""
});

// ── Utilities ─────────────────────────────────────────────────────
function showLoading(msg = "Computing…") {
  document.getElementById("loadingOverlay").classList.add("active");
  document.getElementById("loadingText").textContent = msg;
}
function hideLoading() {
  document.getElementById("loadingOverlay").classList.remove("active");
}
function showToast(msg, type = "info") {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = `toast ${type} show`;
  setTimeout(() => t.classList.remove("show"), 3500);
}
function setStatus(label, online = false) {
  document.getElementById("statusLabel").textContent = label;
  document.getElementById("statusDot").className = "status-dot" + (online ? " online" : "");
}
function badgeHTML(c) {
  const cls = (c || "unknown").toLowerCase();
  return `<span class="badge badge-${cls}">${c || "?"}</span>`;
}
function fmt(node) { return node.replace(/_/g, " "); }

// ── Leaflet picker map init ───────────────────────────────────────
function initPickerMap() {
  pickerMap = L.map("pickerMap", {
    center: [17.42, 78.47],
    zoom: 11,
    zoomControl: true,
  });

  L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
    attribution: "© OpenStreetMap | CartoDB",
    maxZoom: 19,
  }).addTo(pickerMap);

  // Click handler
  pickerMap.on("click", onMapClick);

  // Load all nodes and plot them
  loadNetworkNodes();
}

async function loadNetworkNodes() {
  try {
    const r    = await fetch(`${API_BASE}/api/route/network`);
    const data = await r.json();
    knownNodes = data.node_coords || {};

    document.getElementById("nodeCount").textContent = Object.keys(knownNodes).length;
    document.getElementById("edgeCount").textContent = (data.edges || []).length;

    const HOSPITALS = ["Gandhi_Hospital","Yashoda_Hospital","NIMS_Hospital","Care_Hospital","Apollo_Hospital"];

    for (const [name, coords] of Object.entries(knownNodes)) {
      const [lat, lon] = coords;
      const clean = fmt(name);
      const isHosp = HOSPITALS.includes(name);

      const marker = L.marker([lat, lon], {
        icon: isHosp ? HOSPITAL_ICON : NODE_ICON,
        title: clean,
      }).addTo(pickerMap);

      marker.on("click", (e) => {
        L.DomEvent.stopPropagation(e);
        selectNode(name, lat, lon);
      });

      marker.bindTooltip(clean, { permanent: false, direction: "top", offset: [0, -8] });
    }
  } catch (e) {
    console.warn("Could not load nodes:", e);
  }
}

function onMapClick(e) {
  const { lat, lng } = e.latlng;
  // Snap to nearest known node within 1.5km
  const nearest = findNearestNode(lat, lng);
  if (nearest) {
    selectNode(nearest.name, nearest.lat, nearest.lon);
  } else {
    showToast("Click closer to a known location", "error");
  }
}

function findNearestNode(lat, lng) {
  let best = null, bestDist = 9999;
  for (const [name, coords] of Object.entries(knownNodes)) {
    const d = Math.sqrt(Math.pow(lat - coords[0], 2) + Math.pow(lng - coords[1], 2));
    if (d < bestDist) { bestDist = d; best = { name, lat: coords[0], lon: coords[1] }; }
  }
  // ~1.5km in degrees ≈ 0.014
  return bestDist < 0.020 ? best : null;
}

function selectNode(name, lat, lon) {
  if (currentMode === "origin") {
    if (originMarker) pickerMap.removeLayer(originMarker);
    originMarker = L.marker([lat, lon], { icon: ORIGIN_ICON }).addTo(pickerMap);
    originMarker.bindPopup(`<b>🚑 Origin</b><br>${fmt(name)}`).openPopup();
    originData = { name, lat, lon };
    document.getElementById("originValue").textContent = fmt(name);
    document.getElementById("originCoords").textContent = `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
    document.getElementById("originCard").classList.add("filled");
    document.getElementById("sourceNode").value = name;
    // Auto-switch to destination mode
    setMode("destination");
    showToast(`Origin set: ${fmt(name)}`, "success");
  } else {
    if (destMarker) pickerMap.removeLayer(destMarker);
    destMarker = L.marker([lat, lon], { icon: DEST_ICON }).addTo(pickerMap);
    destMarker.bindPopup(`<b>🎯 Destination</b><br>${fmt(name)}`).openPopup();
    destData = { name, lat, lon };
    document.getElementById("destValue").textContent = fmt(name);
    document.getElementById("destCoords").textContent = `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
    document.getElementById("destCard").classList.add("filled");
    document.getElementById("targetNode").value = name;
    showToast(`Destination set: ${fmt(name)}`, "success");
  }
}

function setMode(mode) {
  currentMode = mode;
  document.getElementById("modeOrigin").classList.toggle("active", mode === "origin");
  document.getElementById("modeDest").classList.toggle("active", mode === "destination");
  document.getElementById("modeHint").textContent =
    mode === "origin" ? "👆 Click on the map to set origin" : "👆 Click on the map to set destination";
}

function selectFromDropdown(type) {
  const sel = document.getElementById(type === "origin" ? "sourceNode" : "targetNode");
  const name = sel.value;
  if (!name || !knownNodes[name]) return;
  const [lat, lon] = knownNodes[name];
  selectNode(name, lat, lon);
  if (type === "origin")      setMode("destination");
}

function clearSelections() {
  if (originMarker) { pickerMap.removeLayer(originMarker); originMarker = null; }
  if (destMarker)   { pickerMap.removeLayer(destMarker);   destMarker   = null; }
  originData = destData = null;
  document.getElementById("originValue").textContent = "Not selected";
  document.getElementById("destValue").textContent   = "Not selected";
  document.getElementById("originCoords").textContent = "";
  document.getElementById("destCoords").textContent   = "";
  document.getElementById("originCard").classList.remove("filled");
  document.getElementById("destCard").classList.remove("filled");
  document.getElementById("sourceNode").value = "";
  document.getElementById("targetNode").value = "";
  setMode("origin");
}

// ── Find Route ────────────────────────────────────────────────────
async function findRoute() {
  const source  = originData?.name || document.getElementById("sourceNode").value;
  const target  = destData?.name   || document.getElementById("targetNode").value;
  if (!source || !target) { showToast("Please set both origin and destination", "error"); return; }
  if (source === target)  { showToast("Origin and destination cannot be the same", "error"); return; }

  const hour    = parseInt(document.getElementById("hourInput").value);
  const day     = document.getElementById("daySelect").value;
  const weather = document.getElementById("weatherSelect").value;

  showLoading("Running Dijkstra + ML prediction…");
  try {
    const res  = await fetch(`${API_BASE}/api/route/find`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source, target, hour, day_of_week: day, weather }),
    });
    const data = await res.json();
    hideLoading();

    if (!data.found) { showToast(`No route: ${data.error || "unknown"}`, "error"); return; }

    renderRouteResult(data);
    renderEdgeTable(data.edges_used);
    if (data.congestion_map) renderRoadList(data.congestion_map);
    document.getElementById("mapLink").href = "/map";
    showToast(`Route: ${data.path.length - 1} hops · ${data.estimated_minutes} min`, "success");

    // Fit map to route
    if (data.path.length >= 2) {
      const pts = data.path.filter(n => knownNodes[n]).map(n => knownNodes[n]);
      if (pts.length >= 2) pickerMap.fitBounds(pts, { padding: [30, 30] });
    }
  } catch (e) {
    hideLoading();
    showToast("Request failed", "error");
  }
}

function renderRouteResult(data) {
  document.getElementById("metricTimeVal").textContent = data.estimated_minutes;
  document.getElementById("metricDistVal").textContent = data.total_distance_km;
  document.getElementById("metricHopsVal").textContent = data.path.length - 1;
  document.getElementById("metricCostVal").textContent = data.total_weight;
  ["metricTime","metricDist","metricHops","metricCost"].forEach(id => document.getElementById(id).classList.add("active"));

  const container = document.getElementById("routePath");
  container.innerHTML = "";
  data.path.forEach((node, i) => {
    const isStart = i === 0, isEnd = i === data.path.length - 1;
    const span = document.createElement("span");
    span.className = `route-node${isStart?" start":isEnd?" end":""}`;
    span.style.animationDelay = `${i * 0.06}s`;
    span.innerHTML = `${isStart?'<i class="fas fa-plus-circle" style="font-size:10px"></i>':''}${isEnd?'<i class="fas fa-map-pin" style="font-size:10px"></i>':''} ${fmt(node)}`;
    container.appendChild(span);
    if (i < data.path.length - 1) {
      const arr = document.createElement("span");
      arr.className = "route-arrow";
      arr.innerHTML = '<i class="fas fa-chevron-right"></i>';
      container.appendChild(arr);
    }
  });
}

function renderEdgeTable(edges) {
  const tbody = document.getElementById("edgeTableBody");
  if (!edges?.length) { tbody.innerHTML = `<tr><td colspan="6" class="empty-row">No data</td></tr>`; return; }
  tbody.innerHTML = edges.map((e, i) => `
    <tr style="animation:slideIn 0.2s ease ${i*0.04}s both">
      <td style="font-weight:600;color:#2a1f1a">${fmt(e.from)}</td>
      <td>${fmt(e.to)}</td>
      <td style="font-family:var(--font-mono);color:#8076a3">${e.road_id}</td>
      <td style="font-family:var(--font-mono)">${e.distance_km}</td>
      <td>${badgeHTML(e.congestion)}</td>
      <td style="font-family:var(--font-mono);color:#7c677f">${e.weight}</td>
    </tr>`).join("");
}

// ── Predict Traffic ───────────────────────────────────────────────
async function predictAllTraffic() {
  const hour = parseInt(document.getElementById("hourInput").value);
  const day  = document.getElementById("daySelect").value;
  const weather = document.getElementById("weatherSelect").value;
  showLoading("Running Random Forest…");
  try {
    const res  = await fetch(`${API_BASE}/api/traffic/predict_all`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ hour, day_of_week: day, weather }),
    });
    const data = await res.json();
    hideLoading();
    if (data.error) { showToast(data.error, "error"); return; }
    renderRoadList(data.congestion_map);
    showToast("Traffic prediction complete", "success");
  } catch { hideLoading(); showToast("Prediction failed", "error"); }
}

const ROAD_TYPES = { R1:"Highway",R2:"Arterial",R3:"Local",R4:"Arterial",R5:"Highway",R6:"Local",R7:"Arterial",R8:"Local" };

function renderRoadList(map) {
  const container = document.getElementById("roadList");
  container.innerHTML = Object.entries(map).map(([rid, level], i) => `
    <div class="road-item" style="animation-delay:${i*0.05}s">
      <span class="road-id">${rid}</span>
      <span class="road-type">${ROAD_TYPES[rid]||"Road"}</span>
      <div class="road-bar-wrap"><div class="road-bar ${(level||"").toLowerCase()}"></div></div>
      ${badgeHTML(level)}
    </div>`).join("");
}

// ── Simulate Incident ─────────────────────────────────────────────
async function simulateIncident() {
  const road_id  = document.getElementById("incidentRoad").value;
  const severity = document.getElementById("incidentSeverity").value;
  showLoading(`Incident on ${road_id}…`);
  try {
    const res  = await fetch(`${API_BASE}/api/route/simulate_incident`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ road_id, severity }),
    });
    const data = await res.json();
    hideLoading();
    const before = data.route_before, after = data.route_after;
    document.getElementById("incidentResult").style.display = "block";
    document.getElementById("beforePath").textContent = before.path?.map(fmt).join(" → ") || "N/A";
    document.getElementById("afterPath").textContent  = after.path?.map(fmt).join(" → ")  || "N/A";
    document.getElementById("beforeTime").textContent = before.estimated_minutes ? `${before.estimated_minutes} min` : "--";
    document.getElementById("afterTime").textContent  = after.estimated_minutes  ? `${after.estimated_minutes} min`  : "--";
    document.getElementById("incidentMessage").innerHTML =
      `${data.route_changed ? "🔄" : "✅"} ${data.message}`;
    if (after.edges_used) renderEdgeTable(after.edges_used);
    if (after.path) renderRouteResult(after);
    showToast(data.message, "info");
  } catch { hideLoading(); showToast("Simulation failed", "error"); }
}

// ── Health check ──────────────────────────────────────────────────
async function checkHealth() {
  try {
    const r = await fetch(`${API_BASE}/health`);
    if (r.ok) { setStatus("System Online", true); showToast("Backend connected ✓", "success"); }
    else setStatus("Degraded");
  } catch { setStatus("Offline — run: python run.py"); showToast("Cannot connect to backend", "error"); }
}

// ── Init ──────────────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => {
  initPickerMap();
  checkHealth();
});
