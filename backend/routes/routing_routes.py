"""
backend/routes/routing_routes.py
---------------------------------
Flask Blueprint for emergency vehicle route optimization endpoints.

Endpoints:
  POST /api/route/find              — compute optimal emergency route
  POST /api/route/reroute           — dynamically update traffic + reroute
  GET  /api/route/network           — get full road network info
  GET  /api/route/map               — serve the live Folium map HTML
  POST /api/route/simulate_incident — simulate a traffic incident
"""

import os
from flask import Blueprint, request, jsonify, send_file
from backend.models.graph_model import RoadNetwork
from backend.models.traffic_model import batch_predict
from backend.utils.visualizer import build_map
from backend.config import Config

routing_bp = Blueprint("routing", __name__, url_prefix="/api/route")

# ─── Shared road network instance (rebuilt per request with fresh weights) ────
# In production you'd use Redis for shared state. For a portfolio project,
# rebuilding the graph per request is fine — it's very fast (<10ms).


def _build_network(congestion_dict: dict = None) -> RoadNetwork:
    return RoadNetwork(Config.ROAD_EDGES, congestion_state=congestion_dict or {})


def _get_current_congestion(hour: int, day: str, weather: str) -> dict:
    """
    Runs ML batch prediction for all roads and returns a {road_id: level} map.
    """
    ROAD_TYPE_MAP = {
        "R1": "highway", "R2": "arterial", "R3": "local",
        "R4": "arterial","R5": "highway",  "R6": "local",
        "R7": "arterial","R8": "local",
    }
    DEFAULT_COUNTS = {
        "R1": 350, "R2": 150, "R3": 60,
        "R4": 160, "R5": 380, "R6": 50,
        "R7": 140, "R8": 45,
    }
    is_wknd = int(day in ["Saturday", "Sunday"])

    road_conditions = [
        {
            "hour": hour, "day_of_week": day, "weather": weather,
            "road_id": rid, "road_type": rtype,
            "vehicle_count": DEFAULT_COUNTS.get(rid, 100),
            "is_weekend": is_wknd,
        }
        for rid, rtype in ROAD_TYPE_MAP.items()
    ]

    preds = batch_predict(road_conditions, Config.MODEL_PATH, Config.ENCODERS_PATH)
    return {rc["road_id"]: p["predicted_class"] for rc, p in zip(road_conditions, preds)}


@routing_bp.route("/find", methods=["POST"])
def find_route():
    """
    Computes the optimal emergency vehicle route.

    Request body:
      {
        "source":      "Hospital",
        "target":      "Accident_Site",
        "hour":        8,
        "day_of_week": "Monday",
        "weather":     "Clear"
      }

    Response:
      {
        "found":             true,
        "path":              ["Hospital", "Junction_A", "Junction_D", "Accident_Site"],
        "total_distance_km": 6.5,
        "estimated_minutes": 9.75,
        "total_weight":      8.25,
        "edges_used":        [...],
        "congestion_map":    {"R1": "Low", "R2": "High", ...},
        "map_url":           "/api/route/map"
      }
    """
    data    = request.get_json(force=True) or {}
    source  = data.get("source",      "Gandhi_Hospital")
    target  = data.get("target",      "Uppal")
    hour    = int(data.get("hour",    12))
    day     = data.get("day_of_week", "Monday")
    weather = data.get("weather",     "Clear")

    # ── Step 1: Predict current congestion on all roads ───────────────────────
    try:
        congestion_map = _get_current_congestion(hour, day, weather)
    except FileNotFoundError:
        # Model not trained yet — use neutral defaults
        congestion_map = {}

    # ── Step 2: Build weighted graph with ML-predicted congestion ─────────────
    network = _build_network(congestion_map)

    # ── Step 3: Run Dijkstra ──────────────────────────────────────────────────
    result = network.dijkstra(source, target)
    result["congestion_map"] = congestion_map
    result["conditions"]     = {"hour": hour, "day": day, "weather": weather}

    if not result.get("found"):
        return jsonify(result), 404

    # ── Step 4: Generate Folium map ───────────────────────────────────────────
    map_path = os.path.join(Config.MAP_OUTPUT_DIR, "map.html")
    try:
        build_map(
            node_coords = Config.NODE_COORDS,
            edges_info  = network.get_all_edges_info(),
            route_path  = result["path"],
            route_edges = result["edges_used"],
            output_path = map_path,
        )
        result["map_url"] = "/map"
    except Exception as e:
        result["map_warning"] = f"Map generation failed: {str(e)}"

    return jsonify(result), 200


@routing_bp.route("/reroute", methods=["POST"])
def dynamic_reroute():
    """
    Simulates a real-time traffic change and recalculates the route.

    Request body:
      {
        "source":         "Hospital",
        "target":         "Accident_Site",
        "hour":           17,
        "day_of_week":    "Friday",
        "weather":        "Rainy",
        "traffic_update": {"R5": "High", "R4": "High"}
      }

    The traffic_update dict overrides ML predictions — simulating an
    incident report or sensor data arriving in real time.
    """
    data    = request.get_json(force=True) or {}
    source  = data.get("source",        "Gandhi_Hospital")
    target  = data.get("target",        "Uppal")
    hour    = int(data.get("hour",      17))
    day     = data.get("day_of_week",   "Friday")
    weather = data.get("weather",       "Rainy")
    updates = data.get("traffic_update",{})

    try:
        congestion_map = _get_current_congestion(hour, day, weather)
    except FileNotFoundError:
        congestion_map = {}

    # Apply real-time overrides
    congestion_map.update(updates)

    network = _build_network(congestion_map)
    result  = network.dijkstra(source, target)
    result["congestion_map"]    = congestion_map
    result["rerouting_trigger"] = updates
    result["conditions"]        = {"hour": hour, "day": day, "weather": weather}

    if result.get("found"):
        map_path = os.path.join(Config.MAP_OUTPUT_DIR, "map.html")
        try:
            build_map(
                node_coords = Config.NODE_COORDS,
                edges_info  = network.get_all_edges_info(),
                route_path  = result["path"],
                route_edges = result["edges_used"],
                output_path = map_path,
            )
            result["map_url"] = "/map"
        except Exception:
            pass

    return jsonify(result), 200 if result.get("found") else 404


@routing_bp.route("/network", methods=["GET"])
def get_network():
    """Returns the full road network structure (nodes + edges)."""
    network = _build_network()
    return jsonify({
        "nodes":       network.get_nodes(),
        "edges":       network.get_all_edges_info(),
        "node_coords": Config.NODE_COORDS,
    }), 200


@routing_bp.route("/simulate_incident", methods=["POST"])
def simulate_incident():
    """
    Simulates a traffic incident on a specific road.

    Useful for the frontend demo: user clicks 'Simulate Incident on R5'
    and sees the route change instantly.

    Request: {"road_id": "R5", "severity": "High"}
    """
    data     = request.get_json(force=True) or {}
    road_id  = data.get("road_id",  "R5")
    severity = data.get("severity", "High")

    # Before incident
    source, target = "Gandhi_Hospital", "Uppal"
    try:
        cong_before = _get_current_congestion(17, "Friday", "Clear")
    except FileNotFoundError:
        cong_before = {}

    net_before = _build_network(cong_before)
    route_before = net_before.dijkstra(source, target)

    # After incident
    cong_after = dict(cong_before)
    cong_after[road_id] = severity
    net_after  = _build_network(cong_after)
    route_after = net_after.dijkstra(source, target)

    # Regenerate map showing post-incident routing
    if route_after.get("found"):
        map_path = os.path.join(Config.MAP_OUTPUT_DIR, "map.html")
        try:
            build_map(
                node_coords = Config.NODE_COORDS,
                edges_info  = net_after.get_all_edges_info(),
                route_path  = route_after["path"],
                route_edges = route_after["edges_used"],
                output_path = map_path,
            )
        except Exception:
            pass

    changed = route_before.get("path") != route_after.get("path")

    return jsonify({
        "incident":      {"road_id": road_id, "severity": severity},
        "route_before":  route_before,
        "route_after":   route_after,
        "route_changed": changed,
        "message": (
            f"Route changed! Avoided {road_id} due to {severity} congestion."
            if changed else
            f"Same route used despite {severity} congestion on {road_id}."
        ),
    }), 200
