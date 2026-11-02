"""
Main routes: the dashboard and a health check.

A Blueprint is a group of related routes. Later days add more Blueprints
(auth, tasks, reminders, notes, chat...) in this same folder.
"""

from flask import Blueprint, current_app, jsonify, render_template
from sqlalchemy import text

from app.extensions import db
from app.models import User
from app.services.dashboard_service import get_dashboard_data, get_empty_dashboard_data

main_bp = Blueprint("main", __name__)


def get_dashboard_user():
    """
    TEMPORARY for Day 6: login does not exist yet, so show the first user.
    Day 7 replaces this with Flask-Login's current_user and protects the page.
    """
    return User.query.order_by(User.id).first()


@main_bp.route("/")
def index():
    """The dashboard, filled with real data from the database."""
    user = get_dashboard_user()
    data = get_dashboard_data(user.id) if user else get_empty_dashboard_data()
    return render_template("dashboard.html", dashboard_user=user, **data)


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
