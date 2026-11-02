"""Small helper functions used in several places."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

from flask_login import current_user

# Only real places, which leaves out old aliases such as "US/Eastern"
TIMEZONE_REGIONS = ("Africa/", "America/", "Asia/", "Atlantic/", "Australia/",
                    "Europe/", "Indian/", "Pacific/")


def utc_now():
    """
    Current time in UTC, without timezone info.

    All times are stored in UTC so they don't depend on where the server is.
    They are converted to the user's own time zone only when displayed.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_timezone_names():
    """The time zones a user can choose from: UTC first, then the rest A to Z."""
    names = [name for name in available_timezones() if name.startswith(TIMEZONE_REGIONS)]
    return ["UTC"] + sorted(names)


def get_user_timezone():
    """The logged-in user's time zone. Visitors, or an unknown zone name, get UTC."""
    name = getattr(current_user, "timezone", None) or "UTC"
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return ZoneInfo("UTC")


def to_user_time(value):
    """Convert a time stored in UTC to the user's own time zone."""
    return value.replace(tzinfo=timezone.utc).astimezone(get_user_timezone())


def datetime_short(value):
    """
    Template filter: shows a stored UTC time in the user's time zone.

    With Europe/Paris, 2026-11-03 14:30 becomes "Tue 03 Nov 2026, 15:30 CET".
    """
    if value is None:
        return ""
    return to_user_time(value).strftime("%a %d %b %Y, %H:%M %Z")
