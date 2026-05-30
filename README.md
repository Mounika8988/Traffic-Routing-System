# Smart Traffic Prediction & Emergency Vehicle Routing System

> An AI-powered intelligent transportation system that reduces emergency response time using **Machine Learning** for congestion prediction and **Dijkstra's Algorithm** for real-time optimal routing.

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-green)](https://flask.palletsprojects.com)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.4-orange)](https://scikit-learn.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## Problem Statement

In modern cities, emergency vehicles (ambulances, fire trucks, police) are frequently delayed by traffic congestion. Traditional GPS systems only optimize for **shortest distance** — they do not:

- Predict future congestion levels
- Dynamically reroute when conditions change
- Prioritize emergency vehicle paths

This system solves all three problems.

---

## Architecture

```
┌────────────────────────────────────────────────────────┐
│                     Frontend (HTML/CSS/JS)              │
│    Dashboard • Route Visualizer • Traffic Heatmap       │
└────────────────────────┬───────────────────────────────┘
                         │  REST API (Flask)
┌────────────────────────▼───────────────────────────────┐
│                    Flask Backend                         │
│  ┌───────────────┐      ┌──────────────────────────┐   │
│  │ Traffic Routes │      │   Routing Routes          │   │
│  │ /predict       │      │   /find  /reroute         │   │
│  └───────┬───────┘      └──────────┬───────────────┘   │
│          │                          │                    │
│  ┌───────▼───────┐      ┌──────────▼───────────────┐   │
│  │  ML Module     │      │   Graph Module            │   │
│  │  Random Forest │      │   Dijkstra Algorithm      │   │
│  └───────┬───────┘      └──────────┬───────────────┘   │
│          │                          │                    │
│  ┌───────▼──────────────────────────▼───────────────┐  │
│  │  Folium Visualizer  •  traffic_data.csv           │  │
│  └───────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

---

## Features

| Feature | Technology |
|---------|-----------|
| Traffic congestion prediction | Random Forest Classifier (98.6% accuracy) |
| Optimal route computation | Dijkstra's Algorithm O((V+E)log V) |
| Dynamic rerouting | Real-time graph weight updates |
| Interactive map | Folium / Leaflet.js |
| REST API | Flask with CORS |
| Frontend Dashboard | HTML5 / CSS3 / Vanilla JS |

---

## Project Structure

```
smart_traffic_system/
├── backend/
│   ├── app.py                    # Flask application factory
│   ├── config.py                 # Centralized configuration
│   ├── models/
│   │   ├── traffic_model.py      # ML prediction interface
│   │   └── graph_model.py        # Graph + Dijkstra implementation
│   ├── utils/
│   │   └── visualizer.py         # Folium map generator
│   ├── routes/
│   │   ├── traffic_routes.py     # /api/traffic/* endpoints
│   │   └── routing_routes.py     # /api/route/* endpoints
│   ├── data/
│   │   └── traffic_data.csv      # 10,000-row simulated dataset
│   └── saved_models/
│       ├── traffic_model.pkl     # Trained Random Forest
│       └── label_encoders.pkl    # Feature encoders
├── frontend/
│   ├── index.html                # Main dashboard
│   ├── static/
│   │   ├── css/style.css         # Dark industrial theme
│   │   └── js/app.js             # API calls + UI logic
│   └── templates/
│       └── map.html              # Generated Folium map
├── scripts/
│   ├── generate_dataset.py       # Synthetic data generator
│   └── train_model.py            # Model training pipeline
├── run.py                        # Entry point
└── requirements.txt
```

---

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/yourusername/smart-traffic-system.git
cd smart-traffic-system

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Generate Dataset & Train Model

```bash
# Step 1: Generate 10,000 rows of simulated traffic data
python scripts/generate_dataset.py

# Step 2: Train the Random Forest classifier
python scripts/train_model.py
# Expected output: Test Accuracy: 98.60%
```

### 3. Run the Application

```bash
python run.py
```

Open your browser: **http://localhost:5000**

---

## API Endpoints

### Traffic Prediction
```http
POST /api/traffic/predict
{
  "hour": 8,
  "day_of_week": "Monday",
  "weather": "Rainy",
  "road_id": "R2",
  "vehicle_count": 180
}
→ {"predicted_class": "High", "confidence": 0.88, ...}
```

### Route Optimization
```http
POST /api/route/find
{
  "source": "Hospital",
  "target": "Accident_Site",
  "hour": 8,
  "day_of_week": "Monday",
  "weather": "Clear"
}
→ {"path": ["Hospital", "Junction_C", ...], "estimated_minutes": 9.7, ...}
```

### Dynamic Rerouting
```http
POST /api/route/reroute
{
  "source": "Hospital",
  "target": "Accident_Site",
  "traffic_update": {"R5": "High", "R4": "High"}
}
```

### Incident Simulation
```http
POST /api/route/simulate_incident
{"road_id": "R5", "severity": "High"}
→ {"route_changed": true, "route_before": {...}, "route_after": {...}}
```

---

## ML Model Performance

```
Test Accuracy: 98.60%
Cross-Validation: 98.12% ± 0.35%

              precision  recall  f1-score
  High           0.99    0.99      0.99
  Low            0.99    0.98      0.99
  Medium         0.97    0.98      0.98

Top Features:
  vehicle_count   47.1%
  hour            31.6%
  weather          9.6%
  road_type        6.5%
```

---

## Road Network

The system models 7 intersections and 11 road segments in Hyderabad:

```
Hospital ──R1──→ Junction_A ──R2──→ Junction_B
   │                  │                  │
   R8               R4                 R7
   │                  ↓                  ↓
   └──────────→ Junction_C ──R5──→ Junction_D ──R6──→ Accident_Site
                                         ↑
                                    City_Center
```

---

## Deployment (Render / Railway)

```bash
# Install gunicorn
pip install gunicorn

# Start production server
gunicorn -w 4 -b 0.0.0.0:5000 "backend.app:create_app()"
```

Set environment variables:
```
SECRET_KEY=your-secret-key-here
DEBUG=False
```

---

## Future Enhancements

- [ ] Live Google Maps / OpenStreetMap integration
- [ ] IoT traffic sensor data ingestion
- [ ] LSTM for time-series traffic forecasting
- [ ] Reinforcement learning for adaptive signal control
- [ ] WebSocket for real-time push updates
- [ ] Mobile app (React Native)
- [ ] Multi-vehicle fleet coordination

---

## Tech Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| ML    | scikit-learn RandomForest | Congestion prediction |
| Graph | NetworkX / Custom | Road network modeling |
| API   | Flask + Flask-CORS | REST backend |
| Maps  | Folium + Leaflet.js | Interactive visualization |
| Data  | Pandas + NumPy | Preprocessing |
| UI    | HTML5/CSS3/JS | Dashboard |

---

