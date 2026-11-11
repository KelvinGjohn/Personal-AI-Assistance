"""
Main routes: the dashboard and a health check.

A Blueprint is a group of related routes. Later days add more Blueprints
(tasks, reminders, notes, chat...) in this same folder.
"""

from flask import Blueprint, current_app, jsonify, render_template
from flask_login import current_user, login_required
from sqlalchemy import text

from app.extensions import db
from app.services.dashboard_service import get_dashboard_data
from app.utils import get_user_timezone

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@login_required
def index():
    """The logged-in user's dashboard. Visitors are redirected to the login page."""
    data = get_dashboard_data(current_user.id, tz=get_user_timezone())
    return render_template("dashboard.html", **data)


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
