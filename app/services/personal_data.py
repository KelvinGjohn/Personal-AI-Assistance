"""
Personal data for the AI (FR-55): a short summary of one user's own tasks,
reminders and notes, so the AI can answer questions like "what's due this week?".

Privacy (NFR-15):
- It is only built when the user ticks "Use my tasks, reminders and notes".
- Every query filters by the user's id, so another user's records can never appear.
- Only what is useful is sent, with limits on how many items and how much text.
"""

import json
from datetime import timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.models import Note, Reminder, Task
from app.utils import utc_now

MAX_OPEN_TASKS = 50
MAX_FINISHED_TASKS = 20
FINISHED_TASK_DAYS = 7
MAX_REMINDERS = 30
MAX_NOTES = 20
MAX_DESCRIPTION = 200
MAX_NOTE_TEXT = 600

TAG = "personal_data"


def get_zone(name):
    try:
        return ZoneInfo(name or "UTC")
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return ZoneInfo("UTC")


def local_text(value, zone):
    """A stored UTC time as readable text in the user's time zone."""
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc).astimezone(zone).strftime("%a %d %b %Y %H:%M")


def shorten(text, limit):
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[:limit].rstrip() + "..."


def collect_personal_data(user, now=None):
    """The user's records as a dictionary, ready to turn into JSON."""
    if now is None:
        now = utc_now()
    zone = get_zone(user.timezone)

    open_tasks = (
        Task.query.filter_by(user_id=user.id, is_completed=False)
        .order_by(Task.due_date.is_(None), Task.due_date, Task.created_at.desc())
        .limit(MAX_OPEN_TASKS).all()
    )
    finished_tasks = (
        Task.query.filter_by(user_id=user.id, is_completed=True)
        .filter(Task.completed_at >= now - timedelta(days=FINISHED_TASK_DAYS))
        .order_by(Task.completed_at.desc())
        .limit(MAX_FINISHED_TASKS).all()
    )
    # Reminders still to come, or due and not yet dealt with
    reminders = (
        Reminder.query.filter_by(user_id=user.id)
        .filter((Reminder.remind_at > now) | (Reminder.is_notified.is_(False)))
        .order_by(Reminder.remind_at)
        .limit(MAX_REMINDERS).all()
    )
    notes = (
        Note.query.filter_by(user_id=user.id)
        .order_by(Note.updated_at.desc())
        .limit(MAX_NOTES).all()
    )

    return {
        "now": local_text(now, zone),
        "time_zone": str(zone.key),
        "unfinished_tasks": [
            {
                "title": task.title,
                "priority": task.priority,
                "category": task.category,
                "due": local_text(task.due_date, zone),
                "overdue": bool(task.due_date and task.due_date < now),
                "details": shorten(task.description, MAX_DESCRIPTION) or None,
            }
            for task in open_tasks
        ],
        f"tasks_finished_in_last_{FINISHED_TASK_DAYS}_days": [
            {"title": task.title, "finished": local_text(task.completed_at, zone)}
            for task in finished_tasks
        ],
        "reminders": [
            {
                "title": reminder.title,
                "at": local_text(reminder.remind_at, zone),
                "status": "due now" if reminder.remind_at <= now else "upcoming",
            }
            for reminder in reminders
        ],
        f"most_recent_{MAX_NOTES}_notes": [
            {
                "title": note.title,
                "category": note.category,
                "edited": local_text(note.updated_at, zone),
                "text": shorten(note.content, MAX_NOTE_TEXT),
            }
            for note in notes
        ],
    }


def build_personal_context(user, now=None):
    """
    The data as text to put before the user's question.

    JSON keeps each record's fields clearly apart. A note can contain any text,
    including the closing tag, so that text is removed: otherwise a note could
    end the data block early and look like part of the question.
    """
    data = json.dumps(collect_personal_data(user, now), ensure_ascii=False, indent=1)
    data = data.replace(f"</{TAG}>", "").replace(f"<{TAG}>", "")
    return f"<{TAG}>\n{data}\n</{TAG}>"


def add_context_to_question(context, question):
    """The text the AI receives for this one message."""
    return f"{context}\n\nMy question: {question}"
