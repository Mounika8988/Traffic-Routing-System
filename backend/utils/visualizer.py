"""
backend/utils/visualizer.py
────────────────────────────
KEY FIX: OSRM is called with ONLY source + destination (not intermediate nodes).
Intermediate Dijkstra nodes are OUR graph waypoints — forcing OSRM to physically
visit every pin causes the loops. OSRM knows the real roads; just give it
start and end, and it draws a clean road-following line automatically.
"""

import os, folium, requests
from folium import plugins
from typing import Optional

CONGESTION_COLOR = {
    "Low":    "#9bc400",
    "Medium": "#e09060",
    "High":   "#c0506a",
    "Unknown":"#c4a8a0",
}

HOSPITAL_NODES = {"Gandhi_Hospital","Yashoda_Hospital","NIMS_Hospital","Care_Hospital","Apollo_Hospital"}
ACCIDENT_NODES = {"Uppal","LB_Nagar","Dilsukhnagar","HITEC_City","Nacharam","Hayathnagar","Vanasthalipuram"}


def _osrm_road_geometry(lat_a, lon_a, lat_b, lon_b):
    """
    Gets road-following geometry between TWO points only.
    Never passes intermediate waypoints — that's what caused the loops.
    """
    try:
        url = (f"http://router.project-osrm.org/route/v1/driving/"
               f"{lon_a},{lat_a};{lon_b},{lat_b}"
               f"?overview=full&geometries=geojson&steps=false")
        r = requests.get(url, timeout=6)
        if r.status_code == 200 and r.json().get("code") == "Ok":
            return [[c[1], c[0]] for c in r.json()["routes"][0]["geometry"]["coordinates"]]
    except Exception:
        pass
    return [[lat_a, lon_a], [lat_b, lon_b]]


def build_map(node_coords, edges_info, route_path=None, route_edges=None,
              center_node="Secunderabad_Station", output_path="map.html"):

    # Auto-center between source and destination
    if route_path and len(route_path) >= 2:
        pts = [node_coords[n] for n in route_path if n in node_coords]
        center = ((min(p[0] for p in pts) + max(p[0] for p in pts)) / 2,
                  (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2)
    else:
        center = node_coords.get(center_node, (17.42, 78.47))

    m = folium.Map(location=center, zoom_start=13,
                   tiles="CartoDB positron", prefer_canvas=True)

    # ── 1. Draw each route SEGMENT separately (colored by its congestion) ────
    # Each segment A→B is one OSRM call from A to B only — NO intermediate stops
    if route_edges:
        for edge in route_edges:
            a, b = edge["from"], edge["to"]
            if a not in node_coords or b not in node_coords:
                continue
            lat_a, lon_a = node_coords[a]
            lat_b, lon_b = node_coords[b]
            cong  = edge.get("congestion", "Unknown")
            color = CONGESTION_COLOR.get(cong, "#c4a8a0")

            # Pure A→B geometry — no loops
            seg = _osrm_road_geometry(lat_a, lon_a, lat_b, lon_b)

            folium.PolyLine(seg, color=color, weight=7,
                            opacity=0.5, tooltip=f"{cong} congestion").add_to(m)

    # ── 2. Emergency route overlay — source to destination ONLY ──────────────
    # This is the clean purple line on top. One OSRM call: start → end.
    if route_path and len(route_path) >= 2:
        src = route_path[0]
        dst = route_path[-1]
        if src in node_coords and dst in node_coords:
            lat_s, lon_s = node_coords[src]
            lat_d, lon_d = node_coords[dst]
            route_coords = _osrm_road_geometry(lat_s, lon_s, lat_d, lon_d)

            folium.PolyLine(route_coords, color="#8076a3",
                            weight=14, opacity=0.18).add_to(m)
            folium.PolyLine(route_coords, color="#8076a3",
                            weight=5,  opacity=1.0,
                            tooltip="🚑 Emergency Route").add_to(m)
            plugins.AntPath(route_coords, color="#7c677f",
                            weight=5, opacity=0.9, delay=700).add_to(m)

    # ── 3. Markers — only source + destination get big pins ──────────────────
    source_node = route_path[0] if route_path else None
    dest_node   = route_path[-1] if route_path else None

    for node, (lat, lon) in node_coords.items():
        clean = node.replace("_", " ")
        if node == source_node:
            folium.Marker([lat, lon],
                tooltip=f"🚑 START: {clean}",
                popup=folium.Popup(f"<b>🚑 Origin</b><br>{clean}", max_width=160),
                icon=folium.Icon(color="red", icon="plus", prefix="fa")).add_to(m)
        elif node == dest_node:
            folium.Marker([lat, lon],
                tooltip=f"🎯 DESTINATION: {clean}",
                popup=folium.Popup(f"<b>🎯 Destination</b><br>{clean}", max_width=160),
                icon=folium.Icon(color="orange", icon="exclamation-triangle", prefix="fa")).add_to(m)
        elif node in HOSPITAL_NODES:
            folium.CircleMarker([lat, lon], radius=6, color="#c0506a",
                fill=True, fill_color="#fdf0f0", fill_opacity=0.9,
                weight=1.5, tooltip=f"🏥 {clean}").add_to(m)
        elif node in ACCIDENT_NODES:
            folium.CircleMarker([lat, lon], radius=5, color="#e09060",
                fill=True, fill_color="#fff5e0", fill_opacity=0.9,
                weight=1.5, tooltip=f"⚠️ {clean}").add_to(m)
        # All other intermediate nodes: completely invisible

    # ── 4. Legend ─────────────────────────────────────────────────────────────
    m.get_root().html.add_child(folium.Element("""
    <div style="position:fixed;bottom:30px;left:30px;z-index:1000;
        background:#fdf8f6;padding:14px 18px;border-radius:10px;
        box-shadow:0 4px 20px rgba(124,103,127,0.2);font-family:sans-serif;
        border:1.5px solid #e8d8d0;min-width:200px">
      <div style="font-weight:700;font-size:13px;margin-bottom:10px;color:#2a1f1a">Traffic Legend</div>
      <div style="display:flex;align-items:center;gap:8px;margin:5px 0">
        <span style="width:28px;height:4px;background:#9bc400;display:inline-block;border-radius:2px"></span>
        <span style="font-size:12px;color:#5a4a44">Low Congestion</span></div>
      <div style="display:flex;align-items:center;gap:8px;margin:5px 0">
        <span style="width:28px;height:4px;background:#e09060;display:inline-block;border-radius:2px"></span>
        <span style="font-size:12px;color:#5a4a44">Medium Congestion</span></div>
      <div style="display:flex;align-items:center;gap:8px;margin:5px 0">
        <span style="width:28px;height:4px;background:#c0506a;display:inline-block;border-radius:2px"></span>
        <span style="font-size:12px;color:#5a4a44">High Congestion</span></div>
      <div style="display:flex;align-items:center;gap:8px;margin:5px 0;border-top:1px solid #e8d8d0;padding-top:8px">
        <span style="width:28px;height:4px;background:#8076a3;display:inline-block;border-radius:2px"></span>
        <span style="font-size:12px;color:#8076a3;font-weight:600">🚑 Emergency Route</span></div>
      <div style="font-size:10px;color:#9a8a84;margin-top:8px">Roads via OpenStreetMap + OSRM</div>
    </div>"""))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    m.save(output_path)
    return output_path
