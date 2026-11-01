"""
Main routes: the home page and a health check.

A Blueprint is a group of related routes. Later days add more Blueprints
(auth, tasks, reminders, notes, chat...) in this same folder.
"""

from datetime import datetime

from flask import Blueprint, current_app, jsonify, render_template

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Home page. Becomes the real dashboard on Days 5-6."""
    return render_template(
        "index.html",
        app_name=current_app.config["APP_NAME"],
        year=datetime.now().year,
    )


@main_bp.route("/health")
def health():
    """Small JSON endpoint to check the server is running (useful for deployment)."""
    return jsonify(status="ok", app=current_app.config["APP_NAME"])
