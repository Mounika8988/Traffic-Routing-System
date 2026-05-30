# Smart Traffic Prediction & Emergency Vehicle Routing System

> An AI-powered intelligent transportation system that reduces emergency response time using **Machine Learning** for congestion prediction and **Dijkstra's Algorithm** for real-time optimal routing.

## Problem Statement

In modern cities, emergency vehicles (ambulances, fire trucks, police) are frequently delayed by traffic congestion. Traditional GPS systems only optimize for **shortest distance** — they do not:

- Predict future congestion levels
- Dynamically reroute when conditions change
- Prioritize emergency vehicle paths

This system solves all three problems.



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

