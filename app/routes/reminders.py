"""Reminder routes: list, create, edit, dismiss, snooze and delete."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms.reminder_forms import ReminderForm, ReminderRequestForm
from app.models import Reminder
from app.services.ai_service import AIServiceError
from app.services.reminder_assistant import suggest_reminder
from app.services.common import paginate_query
from app.services.reminder_service import (
    STATUSES,
    build_reminder_query,
    count_due_reminders,
    dismiss_reminder,
    get_user_reminder_or_404,
    set_reminder_time,
    snooze_reminder,
)
from app.utils import redirect_back, user_time_to_utc, utc_to_user_input

reminders_bp = Blueprint("reminders", __name__, url_prefix="/reminders")


def apply_form_to_reminder(form, reminder):
    """Copy the form's values onto the reminder. An empty description is saved as NULL."""
    reminder.title = form.title.data
    reminder.description = form.description.data or None
    set_reminder_time(reminder, user_time_to_utc(form.remind_at.data))


@reminders_bp.route("")
@login_required
def index():
    # Unknown status values are ignored
    status = request.args.get("status")
    filters = {"status": status} if status in STATUSES else {}

    query = build_reminder_query(current_user.id, **filters)
    pagination = paginate_query(query, request.args.get("page", 1, type=int))
    return render_template(
        "reminders/index.html",
        pagination=pagination,
        filters=filters,
        statuses=STATUSES,
        due_count=count_due_reminders(current_user.id),
    )


@reminders_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    form = ReminderForm()
    if form.validate_on_submit():
        reminder = Reminder(user_id=current_user.id)
        apply_form_to_reminder(form, reminder)
        db.session.add(reminder)
        db.session.commit()
        flash(f'Reminder "{reminder.title}" created.', "success")
        return redirect(url_for("reminders.index"))

    return render_template("reminders/form.html", form=form, heading="New reminder")


@reminders_bp.route("/assist", methods=["GET", "POST"])
@login_required
def assist():
    """
    The user describes a reminder in plain words and gets a filled-in form,
    with a question about anything missing. Nothing is saved here: the form
    posts to reminders.new like a normal new reminder.
    """
    request_form = ReminderRequestForm()
    ai_error = None

    if request_form.validate_on_submit():
        try:
            suggestion = suggest_reminder(request_form.request.data, current_user.timezone)
        except AIServiceError as error:
            ai_error = str(error)
        else:
            # formdata=None: fill the form from the suggestion, not from what was just posted
            form = ReminderForm(formdata=None, data=suggestion.values)
            return render_template(
                "reminders/form.html", form=form, heading="Check the suggested reminder",
                form_action=url_for("reminders.new"), suggestion=suggestion,
            )

    return render_template(
        "assistant/request.html", form=request_form, ai_error=ai_error,
        heading="Create a reminder with AI", manual_url=url_for("reminders.new"),
        example="For example: remind me to call the dentist tomorrow at 10",
    )


@reminders_bp.route("/<int:reminder_id>/edit", methods=["GET", "POST"])
@login_required
def edit(reminder_id):
    reminder = get_user_reminder_or_404(current_user.id, reminder_id)
    form = ReminderForm(obj=reminder, saved_time=reminder.remind_at)

    if form.validate_on_submit():
        apply_form_to_reminder(form, reminder)
        db.session.commit()
        flash(f'Reminder "{reminder.title}" updated.', "success")
        return redirect(url_for("reminders.index"))

    # The database holds UTC, but the form shows the user's own time
    if request.method == "GET":
        form.remind_at.data = utc_to_user_input(reminder.remind_at)

    return render_template("reminders/form.html", form=form, heading="Edit reminder")


@reminders_bp.route("/<int:reminder_id>/dismiss", methods=["POST"])
@login_required
def dismiss(reminder_id):
    dismiss_reminder(get_user_reminder_or_404(current_user.id, reminder_id))
    db.session.commit()
    return redirect_back(url_for("reminders.index"))


@reminders_bp.route("/<int:reminder_id>/snooze", methods=["POST"])
@login_required
def snooze(reminder_id):
    snooze_reminder(get_user_reminder_or_404(current_user.id, reminder_id))
    db.session.commit()
    return redirect_back(url_for("reminders.index"))


@reminders_bp.route("/<int:reminder_id>/delete", methods=["GET", "POST"])
@login_required
def delete(reminder_id):
    """GET asks for confirmation; only the POST actually deletes."""
    reminder = get_user_reminder_or_404(current_user.id, reminder_id)
    if request.method == "POST":
        title = reminder.title
        db.session.delete(reminder)
        db.session.commit()
        flash(f'Reminder "{title}" deleted.', "success")
        return redirect(url_for("reminders.index"))

    return render_template("reminders/confirm_delete.html", reminder=reminder)
