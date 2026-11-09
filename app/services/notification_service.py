"""
Notification service: creates in-app notifications and marks them as read.

There is no background job, so check_for_new_notifications() runs when the
user opens a page. It creates a notification when:
- a reminder's time has come, or
- an unfinished task's due date has passed.

Each notification's link says which reminder or task it is about, and for
which time. Checking for that link is how the same thing is never notified
twice, and a reminder moved to a new time gets a new notification. The
reminder itself isn't changed: it still shows as Due until it is dismissed.
"""

from datetime import timedelta

from app.extensions import db
from app.models import Notification, Reminder, Task
from app.services.common import get_owned_or_404
from app.utils import utc_now

MESSAGE_LENGTH = 255
# Things that became due long ago aren't news. They are still shown in their own lists.
LOOK_BACK = timedelta(days=7)
MAX_NEW_PER_CHECK = 20


def stamp(value):
    return value.strftime("%Y%m%d%H%M")


def reminder_link(reminder):
    return f"/reminders?status=due&reminder={reminder.id}&at={stamp(reminder.remind_at)}"


def task_link(task):
    return f"/tasks?status=overdue&task={task.id}&due={stamp(task.due_date)}"


def check_for_new_notifications(user_id, now=None):
    """
    Create notifications for anything that has just become due, at most
    MAX_NEW_PER_CHECK at a time (the rest follow on the next page). Returns how many.
    """
    if now is None:
        now = utc_now()
    since = now - LOOK_BACK

    reminders = (
        Reminder.query.filter_by(user_id=user_id, is_notified=False)
        .filter(Reminder.remind_at <= now, Reminder.remind_at > since)
        .order_by(Reminder.remind_at).all()
    )
    tasks = (
        Task.query.filter_by(user_id=user_id, is_completed=False)
        .filter(Task.due_date <= now, Task.due_date > since)
        .order_by(Task.due_date).all()
    )
    candidates = [(f"Reminder due: {r.title}", reminder_link(r)) for r in reminders]
    candidates += [(f"Task overdue: {t.title}", task_link(t)) for t in tasks]
    if not candidates:
        return 0

    # Links that already have a notification, in one query. Anything due since
    # `since` can only have been notified after `since`, so older ones aren't needed.
    existing = {
        row.link for row in
        db.session.query(Notification.link)
        .filter(Notification.user_id == user_id, Notification.created_at >= since)
    }

    added = 0
    for message, link in candidates:
        if link in existing:
            continue
        db.session.add(Notification(user_id=user_id, message=message[:MESSAGE_LENGTH], link=link))
        existing.add(link)
        added += 1
        if added == MAX_NEW_PER_CHECK:
            break
    if added:
        db.session.commit()
    return added


def count_unread(user_id):
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()


def build_notification_query(user_id):
    """Unread first, then newest first."""
    return (
        Notification.query.filter_by(user_id=user_id)
        .order_by(Notification.is_read, Notification.created_at.desc(), Notification.id.desc())
    )


def get_user_notification_or_404(user_id, notification_id):
    return get_owned_or_404(Notification, user_id, notification_id)


def mark_all_read(user_id):
    """One UPDATE for all of the user's unread notifications. Returns how many changed."""
    changed = (
        Notification.query.filter_by(user_id=user_id, is_read=False)
        .update({"is_read": True}, synchronize_session=False)
    )
    db.session.commit()
    return changed
