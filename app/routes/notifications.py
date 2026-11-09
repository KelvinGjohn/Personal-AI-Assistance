"""Notification routes: the list, opening one, and marking them as read."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.services.common import paginate_query
from app.services.notification_service import (
    build_notification_query,
    get_user_notification_or_404,
    mark_all_read,
)
from app.utils import is_safe_redirect, redirect_back

notifications_bp = Blueprint("notifications", __name__, url_prefix="/notifications")


@notifications_bp.route("")
@login_required
def index():
    query = build_notification_query(current_user.id)
    pagination = paginate_query(query, request.args.get("page", 1, type=int))
    return render_template("notifications/index.html", pagination=pagination)


@notifications_bp.route("/<int:notification_id>/open", methods=["POST"])
@login_required
def open_notification(notification_id):
    """Marks it read, then goes to the page it is about. POST, because it changes data."""
    notification = get_user_notification_or_404(current_user.id, notification_id)
    notification.is_read = True
    db.session.commit()
    link = notification.link
    return redirect(link if is_safe_redirect(link) else url_for("notifications.index"))


@notifications_bp.route("/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_read(notification_id):
    get_user_notification_or_404(current_user.id, notification_id).is_read = True
    db.session.commit()
    return redirect_back(url_for("notifications.index"))


@notifications_bp.route("/read-all", methods=["POST"])
@login_required
def read_all():
    changed = mark_all_read(current_user.id)
    if changed:
        flash(f"Marked {changed} notification{'' if changed == 1 else 's'} as read.", "success")
    return redirect(url_for("notifications.index"))
