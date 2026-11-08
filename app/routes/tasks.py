"""Task routes: list, create, edit, complete and delete the logged-in user's tasks."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms.task_forms import TaskForm, TaskRequestForm
from app.services.ai_service import AIServiceError
from app.services.task_assistant import suggest_task
from app.models import Task
from app.models.task import PRIORITIES
from app.services.common import paginate_query
from app.services.task_service import (
    STATUSES,
    build_task_query,
    get_user_categories,
    get_user_task_or_404,
    set_task_completed,
)
from app.utils import redirect_back, user_time_to_utc, utc_to_user_input

tasks_bp = Blueprint("tasks", __name__, url_prefix="/tasks")


def read_filters():
    """Read the filters from the URL. Unknown values are ignored."""
    filters = {}
    if request.args.get("status") in STATUSES:
        filters["status"] = request.args["status"]
    if request.args.get("priority") in PRIORITIES:
        filters["priority"] = request.args["priority"]
    if request.args.get("category"):
        filters["category"] = request.args["category"]
    return filters


def apply_form_to_task(form, task):
    """Copy the form's values onto the task. Empty optional fields are saved as NULL."""
    task.title = form.title.data
    task.description = form.description.data or None
    task.priority = form.priority.data
    task.category = form.category.data or None
    task.due_date = user_time_to_utc(form.due_date.data) if form.due_date.data else None


@tasks_bp.route("")
@login_required
def index():
    filters = read_filters()
    query = build_task_query(current_user.id, **filters)
    pagination = paginate_query(query, request.args.get("page", 1, type=int))
    return render_template(
        "tasks/index.html",
        pagination=pagination,
        filters=filters,
        statuses=STATUSES,
        priorities=PRIORITIES,
        categories=get_user_categories(current_user.id),
    )


@tasks_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    form = TaskForm()
    if form.validate_on_submit():
        task = Task(user_id=current_user.id)
        apply_form_to_task(form, task)
        db.session.add(task)
        db.session.commit()
        flash(f'Task "{task.title}" created.', "success")
        return redirect(url_for("tasks.index"))

    return render_template("tasks/form.html", form=form, heading="New task",
                           categories=get_user_categories(current_user.id))


@tasks_bp.route("/assist", methods=["GET", "POST"])
@login_required
def assist():
    """
    The user describes a task in plain words and gets a filled-in task form.
    Nothing is saved here: the form posts to tasks.new like a normal new task.
    """
    request_form = TaskRequestForm()
    ai_error = None
    categories = get_user_categories(current_user.id)

    if request_form.validate_on_submit():
        try:
            suggestion = suggest_task(request_form.request.data, current_user.timezone, categories)
        except AIServiceError as error:
            ai_error = str(error)
        else:
            # formdata=None: fill the form from the suggestion, not from what was just posted
            form = TaskForm(formdata=None, data=suggestion.values)
            return render_template(
                "tasks/form.html", form=form, heading="Check the suggested task",
                form_action=url_for("tasks.new"), categories=categories,
                suggestion=suggestion,
            )

    return render_template(
        "assistant/request.html", form=request_form, ai_error=ai_error,
        heading="Create a task with AI", manual_url=url_for("tasks.new"),
        example="For example: submit the database report by Friday, it's urgent",
    )


@tasks_bp.route("/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def edit(task_id):
    task = get_user_task_or_404(current_user.id, task_id)
    form = TaskForm(obj=task)

    if form.validate_on_submit():
        apply_form_to_task(form, task)
        db.session.commit()
        flash(f'Task "{task.title}" updated.', "success")
        return redirect(url_for("tasks.index"))

    # The database holds UTC, but the form shows the user's own time
    if request.method == "GET" and task.due_date:
        form.due_date.data = utc_to_user_input(task.due_date)

    return render_template("tasks/form.html", form=form, heading="Edit task",
                           categories=get_user_categories(current_user.id))


@tasks_bp.route("/<int:task_id>/complete", methods=["POST"])
@login_required
def complete(task_id):
    set_task_completed(get_user_task_or_404(current_user.id, task_id), True)
    db.session.commit()
    return redirect_back(url_for("tasks.index"))


@tasks_bp.route("/<int:task_id>/reopen", methods=["POST"])
@login_required
def reopen(task_id):
    set_task_completed(get_user_task_or_404(current_user.id, task_id), False)
    db.session.commit()
    return redirect_back(url_for("tasks.index"))


@tasks_bp.route("/<int:task_id>/delete", methods=["GET", "POST"])
@login_required
def delete(task_id):
    """GET asks for confirmation; only the POST actually deletes."""
    task = get_user_task_or_404(current_user.id, task_id)
    if request.method == "POST":
        title = task.title
        db.session.delete(task)
        db.session.commit()
        flash(f'Task "{title}" deleted.', "success")
        return redirect(url_for("tasks.index"))

    return render_template("tasks/confirm_delete.html", task=task)
