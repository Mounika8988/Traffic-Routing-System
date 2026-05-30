"""
backend/models/traffic_model.py
--------------------------------
Loads the saved Random Forest model and exposes a clean predict() interface.

Design pattern: We load the model ONCE at module import time (singleton-like).
This avoids reloading the heavy model on every API request — critical for
performance in a production web server.
"""

import os
import joblib
import numpy as np
from typing import Optional

# We import Config lazily to avoid circular imports
_model    = None
_encoders = None


def _load_artifacts(model_path: str, enc_path: str):
    """
    Loads and caches the trained model and label encoders.
    Called automatically on first predict() call (lazy loading).
    """
    global _model, _encoders
    if _model is None:
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model not found at {model_path}. "
                "Run: python scripts/train_model.py"
            )
        _model    = joblib.load(model_path)
        _encoders = joblib.load(enc_path)
    return _model, _encoders


def predict_congestion(
    hour: int,
    day_of_week: str,
    weather: str,
    road_id: str,
    road_type: str,
    vehicle_count: int,
    is_weekend: int,
    model_path: str,
    enc_path: str,
) -> dict:
    """
    Predicts traffic congestion for a given road segment & conditions.

    Returns a dict with:
      - predicted_class : "Low" | "Medium" | "High"
      - confidence      : float (0–1), highest class probability
      - probabilities   : {Low: p, Medium: p, High: p}

    How it works internally:
      1. Encode categorical inputs using the same LabelEncoders used during training
      2. Stack into a feature vector in the EXACT same column order as training
      3. Call model.predict() and model.predict_proba()
      4. Decode the integer prediction back to a string label
    """
    model, encoders = _load_artifacts(model_path, enc_path)

    # ── Encode categoricals ───────────────────────────────────────────────────
    def safe_encode(enc, value):
        """Handle unseen labels gracefully by defaulting to 0."""
        try:
            return enc.transform([value])[0]
        except ValueError:
            return 0

    day_enc  = safe_encode(encoders["day_of_week"], day_of_week)
    wea_enc  = safe_encode(encoders["weather"],     weather)
    rid_enc  = safe_encode(encoders["road_id"],     road_id)
    rtp_enc  = safe_encode(encoders["road_type"],   road_type)

    # ── Build feature vector (ORDER must match FEATURE_COLS in config) ────────
    features = np.array([[
        hour, day_enc, wea_enc, rid_enc, rtp_enc, vehicle_count, is_weekend
    ]])

    # ── Predict ───────────────────────────────────────────────────────────────
    pred_int  = model.predict(features)[0]
    proba     = model.predict_proba(features)[0]
    le_target = encoders["congestion_level"]
    classes   = le_target.classes_      # ["High", "Low", "Medium"] alphabetical

    pred_label  = le_target.inverse_transform([pred_int])[0]
    confidence  = float(proba[pred_int])
    prob_dict   = {cls: round(float(p), 4) for cls, p in zip(classes, proba)}

    return {
        "predicted_class": pred_label,
        "confidence":      round(confidence, 4),
        "probabilities":   prob_dict,
    }


def batch_predict(road_conditions: list, model_path: str, enc_path: str) -> list:
    """
    Predicts congestion for multiple road segments at once.

    road_conditions: list of dicts, each with the same keys as predict_congestion()
    Returns: list of prediction dicts in the same order.

    Used by the routing module to get congestion on ALL roads simultaneously
    before computing Dijkstra weights — more efficient than calling one-by-one.
    """
    model, encoders = _load_artifacts(model_path, enc_path)

    def safe_encode(enc, value):
        try:
            return enc.transform([value])[0]
        except ValueError:
            return 0

    rows = []
    for rc in road_conditions:
        rows.append([
            rc["hour"],
            safe_encode(encoders["day_of_week"], rc["day_of_week"]),
            safe_encode(encoders["weather"],     rc["weather"]),
            safe_encode(encoders["road_id"],     rc["road_id"]),
            safe_encode(encoders["road_type"],   rc["road_type"]),
            rc["vehicle_count"],
            rc["is_weekend"],
        ])

    X         = np.array(rows)
    preds     = model.predict(X)
    probas    = model.predict_proba(X)
    le_target = encoders["congestion_level"]
    classes   = le_target.classes_

    results = []
    for pred_int, proba in zip(preds, probas):
        label   = le_target.inverse_transform([pred_int])[0]
        conf    = float(proba[pred_int])
        results.append({
            "predicted_class": label,
            "confidence":      round(conf, 4),
            "probabilities":   {c: round(float(p), 4) for c, p in zip(classes, proba)},
        })
    return results
