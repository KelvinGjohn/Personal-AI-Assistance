"""
Dashboard service: collects the numbers and lists shown on the dashboard.

This logic is kept out of the route so that it can be tested on its own and
so the route stays short. Every query filters by user_id, so one user's
dashboard can never include another user's data.
"""

from datetime import timedelta

from app.models import Conversation, Note, Reminder, Task
from app.utils import utc_now

LIST_LIMIT = 5  # How many items each dashboard panel shows


def get_task_stats(user_id, now):
    """Count the user's tasks by status and work out the completion rate."""
    tasks = Task.query.filter_by(user_id=user_id)

    total = tasks.count()
    completed = tasks.filter_by(is_completed=True).count()
    pending = total - completed
    # Overdue: not finished, and the due date has already passed
    overdue = tasks.filter(Task.is_completed.is_(False), Task.due_date < now).count()
    completed_this_week = tasks.filter(
        Task.is_completed.is_(True),
        Task.completed_at >= now - timedelta(days=7),
    ).count()

    # Checking for zero first avoids dividing by zero when there are no tasks
    completion_rate = round(completed / total * 100) if total else 0

    return {
        "total": total,
        "completed": completed,
        "pending": pending,
        "overdue": overdue,
        "completed_this_week": completed_this_week,
        "completion_rate": completion_rate,
    }


def get_tasks_due_soon(user_id, now, limit=LIST_LIMIT):
    """Unfinished tasks that have a due date, earliest first (overdue ones come first)."""
    tasks = (
        Task.query.filter_by(user_id=user_id, is_completed=False)
        .filter(Task.due_date.is_not(None))
        .order_by(Task.due_date)
        .limit(limit)
        .all()
    )
    return [{"task": task, "is_overdue": task.due_date < now} for task in tasks]


def get_upcoming_reminders(user_id, now, limit=LIST_LIMIT):
    """Reminders that are still in the future, soonest first."""
    return (
        Reminder.query.filter_by(user_id=user_id)
        .filter(Reminder.remind_at >= now)
        .order_by(Reminder.remind_at)
        .limit(limit)
        .all()
    )


def get_recent_notes(user_id, limit=LIST_LIMIT):
    """The most recently edited notes."""
    return (
        Note.query.filter_by(user_id=user_id)
        .order_by(Note.updated_at.desc())
        .limit(limit)
        .all()
    )


def build_summary_cards(task_stats, upcoming_reminder_count, note_count, conversation_count):
    """The four cards at the top of the dashboard."""
    return [
        {
            "label": "Pending tasks",
            "icon": "bi-check2-square",
            "value": task_stats["pending"],
            "detail": f"{task_stats['overdue']} overdue · {task_stats['total']} in total",
        },
        {
            "label": "Upcoming reminders",
            "icon": "bi-alarm",
            "value": upcoming_reminder_count,
            "detail": "still to come",
        },
        {
            "label": "Notes",
            "icon": "bi-journal-text",
            "value": note_count,
            "detail": "saved",
        },
        {
            "label": "Conversations",
            "icon": "bi-chat-dots",
            "value": conversation_count,
            "detail": "with the assistant",
        },
    ]


def get_dashboard_data(user_id, now=None):
    """
    Gather everything the dashboard needs for one user.

    `now` can be passed in so tests can use a fixed time.
    """
    if now is None:
        now = utc_now()

    task_stats = get_task_stats(user_id, now)
    upcoming_reminder_count = (
        Reminder.query.filter_by(user_id=user_id).filter(Reminder.remind_at >= now).count()
    )
    note_count = Note.query.filter_by(user_id=user_id).count()
    conversation_count = Conversation.query.filter_by(user_id=user_id).count()

    return {
        "task_stats": task_stats,
        "summary_cards": build_summary_cards(
            task_stats, upcoming_reminder_count, note_count, conversation_count
        ),
        "tasks_due_soon": get_tasks_due_soon(user_id, now),
        "upcoming_reminders": get_upcoming_reminders(user_id, now),
        "recent_notes": get_recent_notes(user_id),
    }


def get_empty_dashboard_data():
    """What the dashboard shows when there is no user in the database yet."""
    return get_dashboard_data(user_id=None)
