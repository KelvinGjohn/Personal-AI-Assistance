"""
Main routes: the home page and a health check.

A Blueprint is a group of related routes. Later days add more Blueprints
(auth, tasks, reminders, notes, chat...) in this same folder.
"""

from flask import Blueprint, current_app, jsonify, render_template
from sqlalchemy import text

from app.extensions import db

main_bp = Blueprint("main", __name__)

# The dashboard's summary cards. Day 6 adds the real numbers from the database.
SUMMARY_CARDS = [
    {"label": "Tasks",         "icon": "bi-check2-square"},
    {"label": "Reminders",     "icon": "bi-alarm"},
    {"label": "Notes",         "icon": "bi-journal-text"},
    {"label": "Conversations", "icon": "bi-chat-dots"},
]


@main_bp.route("/")
def index():
    """The dashboard page (layout only today; connected to real data on Day 6)."""
    return render_template("dashboard.html", summary_cards=SUMMARY_CARDS)


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
