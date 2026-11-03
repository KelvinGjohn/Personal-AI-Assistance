"""
Reminder service: finding, filtering and detecting due reminders.

A reminder is always in one of three states:
    upcoming - its time is still in the future
    due      - its time has passed and the user hasn't dealt with it yet
    past     - its time has passed and the user has dismissed it
"""

from datetime import timedelta

from sqlalchemy import and_, case

from app.models import Reminder
from app.services.common import get_owned_or_404
from app.utils import utc_now, whole_minute

STATUSES = ("due", "upcoming", "past")
SNOOZE_TIME = timedelta(hours=1)


def get_user_reminder_or_404(user_id, reminder_id):
    return get_owned_or_404(Reminder, user_id, reminder_id)


def build_reminder_query(user_id, status=None, now=None):
    """
    The user's reminders, optionally only one status.

    Order: due first, then upcoming, then past, each earliest first. A list
    of only past reminders shows the most recent first.
    """
    if now is None:
        now = utc_now()

    query = Reminder.query.filter_by(user_id=user_id)
    time_has_passed = Reminder.remind_at <= now

    if status == "due":
        query = query.filter(time_has_passed, Reminder.is_notified.is_(False))
    elif status == "upcoming":
        query = query.filter(Reminder.remind_at > now)
    elif status == "past":
        query = query.filter(time_has_passed, Reminder.is_notified.is_(True))
        return query.order_by(Reminder.remind_at.desc(), Reminder.id.desc())

    rank = case(
        (and_(time_has_passed, Reminder.is_notified.is_(False)), 0),
        (Reminder.remind_at > now, 1),
        else_=2,
    )
    return query.order_by(rank, Reminder.remind_at, Reminder.id)


def count_due_reminders(user_id, now=None):
    """How many reminders are waiting for the user. Day 19 turns these into notifications."""
    return build_reminder_query(user_id, "due", now).count()


def set_reminder_time(reminder, new_time):
    """
    Set the time. A new time makes the reminder go off again, even if the old
    one was dismissed. Forms only hold whole minutes, so saving a form without
    changing the time doesn't count as a new time.
    """
    if reminder.remind_at is None or new_time != whole_minute(reminder.remind_at):
        reminder.remind_at = new_time
        reminder.is_notified = False


def dismiss_reminder(reminder):
    """Only a due reminder can be dismissed, so an old open tab can't hide an upcoming one."""
    if reminder.status == "due":
        reminder.is_notified = True


def snooze_reminder(reminder):
    """Remind again later. Only a due reminder can be snoozed."""
    if reminder.status == "due":
        reminder.remind_at = utc_now() + SNOOZE_TIME
