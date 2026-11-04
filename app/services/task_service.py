"""
Task service: finding, filtering and completing tasks.

Every lookup includes user_id, so one user can never reach another user's tasks.
"""

from app.models import Task
from app.services.common import get_owned_or_404
from app.services.common import get_user_categories as get_categories_for
from app.utils import utc_now

STATUSES = ("pending", "overdue", "completed")


def get_user_task_or_404(user_id, task_id):
    return get_owned_or_404(Task, user_id, task_id)


def get_user_categories(user_id):
    """The user's task categories, for the filter and the form suggestions."""
    return get_categories_for(Task, user_id)


def build_task_query(user_id, status=None, priority=None, category=None):
    """
    The user's tasks with any filters applied.

    Order: unfinished first, then earliest due date, with undated tasks after
    dated ones and the newest first among those.
    """
    query = Task.query.filter_by(user_id=user_id)

    if status == "pending":
        query = query.filter_by(is_completed=False)
    elif status == "completed":
        query = query.filter_by(is_completed=True)
    elif status == "overdue":
        query = query.filter(Task.is_completed.is_(False), Task.due_date < utc_now())

    if priority:
        query = query.filter_by(priority=priority)
    if category:
        query = query.filter_by(category=category)

    return query.order_by(
        Task.is_completed,
        Task.due_date.is_(None),
        Task.due_date,
        Task.created_at.desc(),
        Task.id.desc(),
    )


def set_task_completed(task, completed):
    """
    Mark a task finished or not finished. Doing it twice changes nothing, so
    an older tab or a double click can't flip it back or reset the finish time.
    """
    if completed and not task.is_completed:
        task.is_completed = True
        task.completed_at = utc_now()
    elif not completed and task.is_completed:
        task.is_completed = False
        task.completed_at = None
