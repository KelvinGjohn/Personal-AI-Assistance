"""Calendar routes: a day view and a week view of tasks and reminders."""

from flask import Blueprint, render_template, request
from flask_login import current_user, login_required

from app.services.calendar_service import (
    DEFAULT_VIEW,
    VIEWS,
    count_items,
    days_in_view,
    first_day_of_view,
    get_days,
    move_day,
    parse_day,
)
from app.utils import get_user_timezone, to_user_time, utc_now

calendar_bp = Blueprint("calendar", __name__, url_prefix="/calendar")


@calendar_bp.route("")
@login_required
def index():
    # GET with the view and date in the address, so a day can be bookmarked or refreshed
    view = request.args.get("view") if request.args.get("view") in VIEWS else DEFAULT_VIEW
    today = to_user_time(utc_now()).date()
    selected = parse_day(request.args.get("date"), today)

    first_day = first_day_of_view(view, selected)
    number_of_days = days_in_view(view)
    days = get_days(current_user.id, first_day, number_of_days, get_user_timezone(), today)

    return render_template(
        "calendar/index.html",
        view=view,
        selected=selected,
        today_date=today,
        days=days,
        total=count_items(days),
        previous_day=move_day(first_day, -number_of_days),
        next_day=move_day(first_day, number_of_days),
    )
