"""
backend/routes/traffic_routes.py
---------------------------------
Flask Blueprint for all traffic-prediction-related API endpoints.

Blueprint pattern:
  We split routes into separate Blueprints (traffic, routing) instead of
  putting everything in app.py. This is the Flask equivalent of Django apps —
  modular, testable, and production-ready. It also shows interviewers you
  understand Flask architecture.

Endpoints:
  POST /api/traffic/predict          — predict congestion for a single road
  POST /api/traffic/predict_all      — predict congestion for all roads
  GET  /api/traffic/roads            — list all roads in the network
"""

from flask import Blueprint, request, jsonify
from backend.models.traffic_model import predict_congestion, batch_predict
from backend.config import Config

traffic_bp = Blueprint("traffic", __name__, url_prefix="/api/traffic")

# ─── Road type lookup (same as training data) ─────────────────────────────────
ROAD_TYPE_MAP = {
    "R1": "highway", "R2": "arterial", "R3": "local",
    "R4": "arterial","R5": "highway",  "R6": "local",
    "R7": "arterial","R8": "local",
}
DAYS_OF_WEEK = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]


@traffic_bp.route("/predict", methods=["POST"])
def predict_single():
    """
    Predict congestion for ONE road segment.

    Request body (JSON):
      {
        "hour":          8,
        "day_of_week":   "Monday",
        "weather":       "Rainy",
        "road_id":       "R2",
        "vehicle_count": 150
      }

    Response:
      {
        "road_id":         "R2",
        "predicted_class": "High",
        "confidence":      0.87,
        "probabilities":   {"High": 0.87, "Low": 0.02, "Medium": 0.11}
      }
    """
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "No JSON body provided"}), 400

    # ── Validate required fields ──────────────────────────────────────────────
    required = ["hour", "day_of_week", "weather", "road_id", "vehicle_count"]
    missing  = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 422

    road_id  = data["road_id"]
    road_type = ROAD_TYPE_MAP.get(road_id, "local")
    day      = data["day_of_week"]
    is_wknd  = int(day in ["Saturday", "Sunday"])

    try:
        result = predict_congestion(
            hour          = int(data["hour"]),
            day_of_week   = day,
            weather       = data["weather"],
            road_id       = road_id,
            road_type     = road_type,
            vehicle_count = int(data["vehicle_count"]),
            is_weekend    = is_wknd,
            model_path    = Config.MODEL_PATH,
            enc_path      = Config.ENCODERS_PATH,
        )
        result["road_id"] = road_id
        return jsonify(result), 200

    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 500


@traffic_bp.route("/predict_all", methods=["POST"])
def predict_all_roads():
    """
    Predict congestion for ALL roads simultaneously given current conditions.

    Request body:
      {
        "hour":          17,
        "day_of_week":   "Friday",
        "weather":       "Clear",
        "vehicle_counts": {"R1": 400, "R2": 180, ...}   // optional
      }

    Returns a dict of {road_id: congestion_level} for the whole network.
    This is the main entry point called before Dijkstra runs, so we have
    up-to-date weights for every edge.
    """
    data = request.get_json(force=True) or {}

    hour        = int(data.get("hour", 12))
    day         = data.get("day_of_week", "Monday")
    weather     = data.get("weather", "Clear")
    veh_counts  = data.get("vehicle_counts", {})
    is_wknd     = int(day in ["Saturday", "Sunday"])

    # Default vehicle counts if not provided
    DEFAULT_COUNTS = {
        "R1": 350, "R2": 150, "R3": 60,
        "R4": 160, "R5": 380, "R6": 50,
        "R7": 140, "R8": 45,
    }
    veh_counts = {**DEFAULT_COUNTS, **veh_counts}

    road_conditions = []
    for road_id, road_type in ROAD_TYPE_MAP.items():
        road_conditions.append({
            "hour":          hour,
            "day_of_week":   day,
            "weather":       weather,
            "road_id":       road_id,
            "road_type":     road_type,
            "vehicle_count": veh_counts.get(road_id, 100),
            "is_weekend":    is_wknd,
        })

    try:
        predictions = batch_predict(
            road_conditions,
            model_path = Config.MODEL_PATH,
            enc_path   = Config.ENCODERS_PATH,
        )
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 503

    # Build {road_id: congestion_level} map
    congestion_map = {}
    detailed       = {}
    for rc, pred in zip(road_conditions, predictions):
        rid = rc["road_id"]
        congestion_map[rid] = pred["predicted_class"]
        detailed[rid] = pred

    return jsonify({
        "congestion_map":  congestion_map,
        "detailed":        detailed,
        "conditions_used": {"hour": hour, "day": day, "weather": weather},
    }), 200


@traffic_bp.route("/roads", methods=["GET"])
def list_roads():
    """Returns all road IDs and their types."""
    return jsonify({
        "roads": [
            {"road_id": rid, "road_type": rtype}
            for rid, rtype in ROAD_TYPE_MAP.items()
        ]
    }), 200
