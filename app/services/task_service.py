"""
Task service: finding, filtering and completing tasks.

Every lookup includes user_id, so one user can never reach another user's tasks.
"""

from flask import abort

from app.extensions import db
from app.models import Task
from app.utils import utc_now

TASKS_PER_PAGE = 20
STATUSES = ("pending", "overdue", "completed")
MAX_DATABASE_ID = 2 ** 63 - 1  # Larger numbers can't be sent to SQLite at all


def get_user_task_or_404(user_id, task_id):
    """
    Return the task only if it belongs to this user.

    Another user's task gets the same 404 as a task that doesn't exist, so
    nobody can find out which task ids are in use.
    """
    if task_id > MAX_DATABASE_ID:
        abort(404)
    return Task.query.filter_by(id=task_id, user_id=user_id).first_or_404()


def get_user_categories(user_id):
    """The user's categories, A to Z, for the filter and the form suggestions."""
    rows = (
        db.session.query(Task.category)
        .filter(Task.user_id == user_id, Task.category.is_not(None))
        .distinct()
        .order_by(Task.category)
        .all()
    )
    return [row.category for row in rows]


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


def get_tasks_page(query, page):
    """One page of results. A page number that is too low or too high is corrected."""
    total = query.count()
    last_page = max((total + TASKS_PER_PAGE - 1) // TASKS_PER_PAGE, 1)
    page = min(max(page, 1), last_page)
    return query.paginate(page=page, per_page=TASKS_PER_PAGE, error_out=False)


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
