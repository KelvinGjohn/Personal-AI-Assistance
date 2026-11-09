"""
Sidebar navigation.

The menu is defined once here as data, so adding a page later means adding
one line. Each item names the route (endpoint) it links to and the day the
page is built. Until that route exists, the template shows the item as
disabled with a "Day N" badge instead of a broken link.
"""

from flask import current_app, request
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError

from app.services.notification_service import count_unread
from app.utils import to_user_time, utc_now

NAV_ITEMS = [
    {"label": "Dashboard",     "icon": "bi-grid-1x2",      "endpoint": "main.index",          "day": 5},
    {"label": "AI Assistant",  "icon": "bi-chat-dots",     "endpoint": "chat.index",          "day": 13},
    {"label": "Tasks",         "icon": "bi-check2-square", "endpoint": "tasks.index",         "day": 9},
    {"label": "Reminders",     "icon": "bi-alarm",         "endpoint": "reminders.index",     "day": 10},
    {"label": "Notes",         "icon": "bi-journal-text",  "endpoint": "notes.index",         "day": 11},
    {"label": "Calendar",      "icon": "bi-calendar3",     "endpoint": "calendar.index",      "day": 21},
    {"label": "Search",        "icon": "bi-search",        "endpoint": "search.index",        "day": 20},
    {"label": "Notifications", "icon": "bi-bell",          "endpoint": "notifications.index", "day": 19},
    {"label": "Settings",      "icon": "bi-gear",          "endpoint": "settings.index",      "day": 8},
]


def build_nav_items():
    """Return the menu with two extra fields per item: is_available and is_active."""
    items = []
    for item in NAV_ITEMS:
        items.append({
            **item,
            "is_available": item["endpoint"] in current_app.view_functions,
            # Every page in a Blueprint (such as /tasks/new) highlights its menu item
            "is_active": request.blueprint == item["endpoint"].split(".")[0],
        })
    return items


def inject_layout_data():
    """
    Context processor: the values returned here are available in EVERY template,
    so base.html can draw the sidebar and header without each route passing them.
    """
    return {
        "nav_items": build_nav_items(),
        "app_name": current_app.config["APP_NAME"],
        "today": to_user_time(utc_now()),
        # For the bell in the header
        "unread_count": safe_unread_count(),
    }


def safe_unread_count():
    """
    Every page shows this, including the error page. If the database itself is
    the problem, the bell shows nothing instead of breaking the error page too.
    """
    if not current_user.is_authenticated:
        return 0
    try:
        return count_unread(current_user.id)
    except SQLAlchemyError:
        current_app.logger.exception("Couldn't count unread notifications")
        return 0
