"""
config.py — loads road network from JSON (built by build_road_network.py)
"""
import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def _load_network():
    path = os.path.join(BASE_DIR, "data", "hyderabad_network.json")
    if os.path.exists(path):
        with open(path) as f:
            net = json.load(f)
        edges = [(e["from"], e["to"], e["distance_km"], e["road_id"]) for e in net["edges"]]
        coords = {k: tuple(v) for k, v in net["nodes"].items()}
        return edges, coords
    # Fallback minimal network
    return [], {}

_edges, _coords = _load_network()

class Config:
    SECRET_KEY     = os.environ.get("SECRET_KEY", "smart-traffic-dev-key-2024")
    DEBUG          = os.environ.get("DEBUG", "True").lower() == "true"

    DATA_PATH      = os.path.join(BASE_DIR, "data",         "traffic_data.csv")
    MODEL_PATH     = os.path.join(BASE_DIR, "saved_models", "traffic_model.pkl")
    ENCODERS_PATH  = os.path.join(BASE_DIR, "saved_models", "label_encoders.pkl")
    MAP_OUTPUT_DIR = os.path.join(BASE_DIR, "..", "frontend", "templates")

    FEATURE_COLS     = ["hour", "day_of_week", "weather", "road_id", "road_type", "vehicle_count", "is_weekend"]
    CATEGORICAL_COLS = ["day_of_week", "weather", "road_id", "road_type"]

    ROAD_EDGES   = _edges
    NODE_COORDS  = _coords

    CONGESTION_DELAY = {"Low": 1.0, "Medium": 2.0, "High": 4.5, None: 1.5}
