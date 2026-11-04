"""
Note service: finding, filtering and searching notes.

Every lookup includes user_id, so one user can never reach another user's notes.
"""

from sqlalchemy import or_

from app.models import Note
from app.services.common import get_owned_or_404
from app.services.common import get_user_categories as get_categories_for

MAX_SEARCH_LENGTH = 100


def get_user_note_or_404(user_id, note_id):
    return get_owned_or_404(Note, user_id, note_id)


def get_user_categories(user_id):
    """The user's note categories, for the filter and the form suggestions."""
    return get_categories_for(Note, user_id)


def clean_search_text(text):
    """Remove extra spaces and limit the length of what the user typed."""
    return " ".join((text or "").split())[:MAX_SEARCH_LENGTH].strip()


def build_note_query(user_id, q=None, category=None):
    """
    The user's notes, most recently edited first.

    q is search text. Every word must appear somewhere in the title, content
    or category, so "bank card" also finds "the card from my bank".

    autoescape=True makes % and _ ordinary characters. In SQL LIKE they are
    wildcards, so searching for "100%" would otherwise match anything
    starting with "100".
    """
    query = Note.query.filter_by(user_id=user_id)

    if category:
        query = query.filter_by(category=category)

    for word in (q or "").split():
        query = query.filter(or_(
            Note.title.icontains(word, autoescape=True),
            Note.content.icontains(word, autoescape=True),
            Note.category.icontains(word, autoescape=True),
        ))

    return query.order_by(Note.updated_at.desc(), Note.id.desc())
