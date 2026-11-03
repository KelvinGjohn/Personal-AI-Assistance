"""Helpers shared by every module whose records belong to one user."""

from flask import abort

ITEMS_PER_PAGE = 20
MAX_DATABASE_ID = 2 ** 63 - 1  # Larger numbers can't be sent to SQLite at all


def get_owned_or_404(model, user_id, record_id):
    """
    Return the record only if it belongs to this user.

    Another user's record gets the same 404 as one that doesn't exist, so
    nobody can find out which ids are in use.
    """
    if record_id > MAX_DATABASE_ID:
        abort(404)
    return model.query.filter_by(id=record_id, user_id=user_id).first_or_404()


def paginate_query(query, page):
    """One page of results. A page number that is too low or too high is corrected."""
    total = query.count()
    last_page = max((total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE, 1)
    page = min(max(page, 1), last_page)
    return query.paginate(page=page, per_page=ITEMS_PER_PAGE, error_out=False)
