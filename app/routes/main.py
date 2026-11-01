"""
Main routes: the home page and a health check.

A Blueprint is a group of related routes. Later days add more Blueprints
(auth, tasks, reminders, notes, chat...) in this same folder.
"""

from datetime import datetime

from flask import Blueprint, current_app, jsonify, render_template
from sqlalchemy import text

from app.extensions import db

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
    """Small JSON endpoint to check the server and database are working (useful for deployment)."""
    try:
        db.session.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "error"

    status = "ok" if database == "ok" else "error"
    return jsonify(status=status, database=database, app=current_app.config["APP_NAME"]), \
        (200 if status == "ok" else 503)
