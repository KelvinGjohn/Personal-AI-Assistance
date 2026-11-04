"""Note routes: list and search, view, create, edit and delete."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms.note_forms import NoteForm
from app.models import Note
from app.services.common import paginate_query
from app.services.note_service import (
    MAX_SEARCH_LENGTH,
    build_note_query,
    clean_search_text,
    get_user_categories,
    get_user_note_or_404,
)

notes_bp = Blueprint("notes", __name__, url_prefix="/notes")


def read_filters():
    """Read the search text and category from the URL. Empty values are left out."""
    filters = {}
    q = clean_search_text(request.args.get("q"))
    if q:
        filters["q"] = q
    if request.args.get("category"):
        filters["category"] = request.args["category"]
    return filters


def apply_form_to_note(form, note):
    """Copy the form's values onto the note. An empty category is saved as NULL."""
    note.title = form.title.data
    note.content = form.content.data or ""
    note.category = form.category.data or None


@notes_bp.route("")
@login_required
def index():
    filters = read_filters()
    query = build_note_query(current_user.id, **filters)
    pagination = paginate_query(query, request.args.get("page", 1, type=int))
    return render_template(
        "notes/index.html",
        pagination=pagination,
        filters=filters,
        categories=get_user_categories(current_user.id),
        max_search_length=MAX_SEARCH_LENGTH,
    )


@notes_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    form = NoteForm()
    if form.validate_on_submit():
        note = Note(user_id=current_user.id)
        apply_form_to_note(form, note)
        db.session.add(note)
        db.session.commit()
        flash(f'Note "{note.title}" created.', "success")
        return redirect(url_for("notes.view", note_id=note.id))

    return render_template("notes/form.html", form=form, heading="New note",
                           cancel_url=url_for("notes.index"),
                           categories=get_user_categories(current_user.id))


@notes_bp.route("/<int:note_id>")
@login_required
def view(note_id):
    return render_template("notes/view.html", note=get_user_note_or_404(current_user.id, note_id))


@notes_bp.route("/<int:note_id>/edit", methods=["GET", "POST"])
@login_required
def edit(note_id):
    note = get_user_note_or_404(current_user.id, note_id)
    form = NoteForm(obj=note)

    if form.validate_on_submit():
        apply_form_to_note(form, note)
        db.session.commit()
        flash(f'Note "{note.title}" updated.', "success")
        return redirect(url_for("notes.view", note_id=note.id))

    return render_template("notes/form.html", form=form, heading="Edit note",
                           cancel_url=url_for("notes.view", note_id=note.id),
                           categories=get_user_categories(current_user.id))


@notes_bp.route("/<int:note_id>/delete", methods=["GET", "POST"])
@login_required
def delete(note_id):
    """GET asks for confirmation; only the POST actually deletes."""
    note = get_user_note_or_404(current_user.id, note_id)
    if request.method == "POST":
        title = note.title
        db.session.delete(note)
        db.session.commit()
        flash(f'Note "{title}" deleted.', "success")
        return redirect(url_for("notes.index"))

    return render_template("notes/confirm_delete.html", note=note)
