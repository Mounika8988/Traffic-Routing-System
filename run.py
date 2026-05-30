"""
run.py
------
Entry point for running the Smart Traffic System server.

Run with:
    python run.py

The server starts at:
    http://localhost:5000
"""

import os
import sys

# Ensure project root is in Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app import create_app

app = create_app()

if __name__ == "__main__":
    print("=" * 60)
    print("  🚦 Smart Traffic & Emergency Routing System")
    print("=" * 60)
    print("  Dashboard  → http://localhost:5000")
    print("  API Health → http://localhost:5000/health")
    print("  Live Map   → http://localhost:5000/map  (after first route)")
    print("=" * 60)
    app.run(
        host  = "0.0.0.0",
        port  = 5000,
        debug = True,
    )
