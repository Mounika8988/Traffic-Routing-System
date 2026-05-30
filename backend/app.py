"""
backend/app.py
--------------
Main Flask application factory.

Using the application factory pattern:
  - create_app() function creates and configures the Flask app
  - This allows easy testing (create a test app with different config)
  - Industry-standard pattern — interviewers will recognize it
"""

import os
import sys
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS

# Add parent directory to path so imports work from any run location
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import Config
from backend.routes.traffic_routes import traffic_bp
from backend.routes.routing_routes import routing_bp


def create_app(config_class=Config) -> Flask:
    """
    Creates and configures the Flask application.

    Why application factory?
      - Enables testing with different configurations
      - Prevents circular imports
      - Allows multiple app instances (e.g., for multiprocessing)
    """
    app = Flask(
        __name__,
        template_folder=os.path.join(
            os.path.dirname(__file__), "..", "frontend", "templates"
        ),
        static_folder=os.path.join(
            os.path.dirname(__file__), "..", "frontend", "static"
        ),
    )

    app.config.from_object(config_class)

    # ── CORS — allow frontend to call backend API ──────────────────────────
    # In production, replace "*" with your actual frontend domain
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # ── Register Blueprints ────────────────────────────────────────────────
    app.register_blueprint(traffic_bp)
    app.register_blueprint(routing_bp)

    # ── Serve Frontend ─────────────────────────────────────────────────────
    @app.route("/")
    def index():
        """Serve the main dashboard HTML."""
        return send_from_directory(
            os.path.join(os.path.dirname(__file__), "..", "frontend"),
            "index.html"
        )

    @app.route("/map")
    def serve_map():
        """Serve the generated Folium map HTML."""
        map_path = os.path.join(
            os.path.dirname(__file__), "..", "frontend", "templates", "map.html"
        )
        if os.path.exists(map_path):
            return send_from_directory(
                os.path.join(os.path.dirname(__file__), "..", "frontend", "templates"),
                "map.html"
            )
        return jsonify({"error": "Map not generated yet. Run a route query first."}), 404

    # ── Health check ───────────────────────────────────────────────────────
    @app.route("/health")
    def health():
        """Simple health endpoint — useful for deployment (load balancers ping this)."""
        return jsonify({"status": "ok", "service": "Smart Traffic System"}), 200

    # ── Error handlers ─────────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error", "detail": str(e)}), 500

    return app


# ── Module init files ──────────────────────────────────────────────────────────
# Create __init__.py files so Python treats these as packages
_init_dirs = [
    os.path.join(os.path.dirname(__file__), "models"),
    os.path.join(os.path.dirname(__file__), "utils"),
    os.path.join(os.path.dirname(__file__), "routes"),
]
for d in _init_dirs:
    init_file = os.path.join(d, "__init__.py")
    if not os.path.exists(init_file):
        open(init_file, "w").close()
