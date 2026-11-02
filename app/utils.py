"""Small helper functions used in several places."""

from datetime import datetime, timezone


def utc_now():
    """
    Current time in UTC, without timezone info.

    All times are stored in UTC so they don't depend on where the server is.
    They are converted to the user's own time zone only when displayed (Day 8).
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def datetime_short(value):
    """
    Template filter: 2026-11-03 14:30 becomes "Tue 03 Nov 2026, 14:30 UTC".

    It says UTC so the time is never misleading. Day 8 converts it to the
    user's own time zone.
    """
    if value is None:
        return ""
    return value.strftime("%a %d %b %Y, %H:%M UTC")
