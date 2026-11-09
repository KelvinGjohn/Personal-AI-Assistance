"""Search route: one search box for tasks, reminders, notes and chats."""

from flask import Blueprint, render_template, request
from flask_login import current_user, login_required

from app.services.note_service import MAX_SEARCH_LENGTH, clean_search_text
from app.services.search_service import SINGLE_TYPE_COUNT, TYPE_LABELS, TYPES, search
from app.utils import datetime_short

search_bp = Blueprint("search", __name__, url_prefix="/search")


@search_bp.route("")
@login_required
def index():
    # GET, so a search has its own address and can be refreshed or bookmarked
    q = clean_search_text(request.args.get("q"))
    only_type = request.args.get("type") if request.args.get("type") in TYPES else ""
    groups = search(current_user.id, q, only_type, datetime_short)
    return render_template(
        "search/index.html",
        q=q,
        only_type=only_type,
        groups=groups,
        total=sum(group.total for group in groups),
        types=TYPES,
        type_labels=TYPE_LABELS,
        max_search_length=MAX_SEARCH_LENGTH,
        single_type_count=SINGLE_TYPE_COUNT,
    )
