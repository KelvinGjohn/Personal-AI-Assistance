"""Small helper functions used in several places."""

from datetime import datetime, timezone


def utc_now():
    """
    Current time in UTC, without timezone info.

    All times are stored in UTC so they don't depend on where the server is.
    They are converted to the user's own time zone only when displayed (Day 8).
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
