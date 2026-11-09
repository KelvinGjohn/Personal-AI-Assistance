"""
Note service: finding, filtering and searching notes.

Every lookup includes user_id, so one user can never reach another user's notes.
"""

from app.models import Note
from app.services.common import get_owned_or_404
from app.services.common import get_user_categories as get_categories_for
from app.text_search import all_words_match

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
    or category, so "bank card" also finds "the card from my bank". Upper and
    lower case and accents are ignored, and % and _ are ordinary characters
    (see app/text_search.py).
    """
    query = Note.query.filter_by(user_id=user_id)

    if category:
        query = query.filter_by(category=category)

    condition = all_words_match([Note.title, Note.content, Note.category], q)
    if condition is not None:
        query = query.filter(condition)

    return query.order_by(Note.updated_at.desc(), Note.id.desc())
