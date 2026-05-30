"""
generate_dataset.py
-------------------
Generates a realistic simulated traffic dataset for training the ML model.

Why we need this:
  Real-world traffic datasets require licensing or API keys. For a portfolio
  project, a well-designed synthetic dataset is perfectly acceptable and often
  BETTER because you control its properties and can explain it in interviews.

What this script does:
  - Creates 10,000 rows of traffic observations
  - Encodes real-world patterns: rush hour peaks, weekend differences,
    weather effects on congestion, road-type differences
  - Saves the dataset to backend/data/traffic_data.csv
"""

import pandas as pd
import numpy as np
import os
import random

# ─── Reproducibility ──────────────────────────────────────────────────────────
random.seed(42)
np.random.seed(42)

# ─── Constants ────────────────────────────────────────────────────────────────
NUM_ROWS     = 10_000
ROAD_IDS     = ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"]
ROAD_TYPES   = {
    "R1": "highway",   "R2": "arterial",  "R3": "local",
    "R4": "arterial",  "R5": "highway",   "R6": "local",
    "R7": "arterial",  "R8": "local",
}
ROAD_CAPACITY = {
    "highway": 500, "arterial": 200, "local": 80
}
DAYS         = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
WEATHERS     = ["Clear","Cloudy","Rainy","Foggy","Stormy"]
WEATHER_MULT = {"Clear": 1.0, "Cloudy": 1.1, "Rainy": 1.35, "Foggy": 1.25, "Stormy": 1.5}

# ─── Helper: simulate vehicle count with real-world patterns ──────────────────
def simulate_vehicle_count(hour: int, day: str, weather: str, road_id: str) -> int:
    road_type   = ROAD_TYPES[road_id]
    base_cap    = ROAD_CAPACITY[road_type]
    is_weekday  = day in ["Monday","Tuesday","Wednesday","Thursday","Friday"]

    # Base pattern — daily curve (peaks at 8-9 AM and 5-7 PM on weekdays)
    if is_weekday:
        if 7 <= hour <= 9:
            load = random.uniform(0.75, 0.95)   # Morning rush
        elif 17 <= hour <= 19:
            load = random.uniform(0.70, 0.90)   # Evening rush
        elif 12 <= hour <= 13:
            load = random.uniform(0.50, 0.65)   # Lunch bump
        elif 0 <= hour <= 5:
            load = random.uniform(0.05, 0.15)   # Late night
        else:
            load = random.uniform(0.25, 0.50)   # Midday normal
    else:
        # Weekend: midday peak, no commute rush
        if 10 <= hour <= 14:
            load = random.uniform(0.50, 0.70)
        elif 0 <= hour <= 6:
            load = random.uniform(0.05, 0.12)
        else:
            load = random.uniform(0.20, 0.45)

    # Weather multiplier increases "effective" congestion load
    load *= WEATHER_MULT[weather]
    load = min(load, 1.0)

    vehicle_count = int(base_cap * load + random.uniform(-5, 5))
    return max(0, vehicle_count)


def classify_congestion(vehicle_count: int, road_id: str, weather: str) -> str:
    """
    Classifies traffic into Low / Medium / High based on
    vehicle count relative to road capacity, adjusted for weather.
    """
    capacity    = ROAD_CAPACITY[ROAD_TYPES[road_id]]
    ratio       = vehicle_count / capacity * WEATHER_MULT[weather]

    if ratio < 0.45:
        return "Low"
    elif ratio < 0.80:
        return "Medium"
    else:
        return "High"


def generate_dataset() -> pd.DataFrame:
    rows = []
    for _ in range(NUM_ROWS):
        hour    = random.randint(0, 23)
        day     = random.choice(DAYS)
        weather = random.choice(WEATHERS)
        road_id = random.choice(ROAD_IDS)

        vehicles   = simulate_vehicle_count(hour, day, weather, road_id)
        congestion = classify_congestion(vehicles, road_id, weather)

        rows.append({
            "hour":             hour,
            "day_of_week":      day,
            "weather":          weather,
            "road_id":          road_id,
            "road_type":        ROAD_TYPES[road_id],
            "vehicle_count":    vehicles,
            "is_weekend":       int(day in ["Saturday", "Sunday"]),
            "congestion_level": congestion,
        })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    output_path = os.path.join(
        os.path.dirname(__file__), "..", "backend", "data", "traffic_data.csv"
    )
    df = generate_dataset()

    # Quick sanity print
    print("=" * 50)
    print(f"Dataset shape : {df.shape}")
    print("\nCongestion distribution:")
    print(df["congestion_level"].value_counts())
    print("\nSample rows:")
    print(df.head(5).to_string())
    print("=" * 50)

    df.to_csv(output_path, index=False)
    print(f"\n✅  Dataset saved → {output_path}")
