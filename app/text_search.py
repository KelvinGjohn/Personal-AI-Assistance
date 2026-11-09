"""
Text search helpers shared by notes search and the global search page.

SQLite's own case-insensitive matching (LIKE) only works for English letters:
"CAFÉ" doesn't find "Café". So the app gives SQLite a Python function, fold(),
that both sides are passed through before comparing:

    fold("Café")  -> "cafe"
    fold("CAFÉ")  -> "cafe"
    fold("Straße") -> "strasse"

Matching uses instr() (the position of one text inside another) instead of
LIKE, so % and _ are ordinary characters with no escaping needed.
"""

import unicodedata

from sqlalchemy import and_, func, or_

MAX_WORDS = 10


def fold(text):
    """Lower-case the text properly and remove accents. None stays None."""
    if text is None:
        return None
    # NFKD splits "é" into "e" plus a separate accent mark, which is then dropped
    decomposed = unicodedata.normalize("NFKD", str(text).casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def search_words(q):
    """
    The search text as a list of folded words, at most MAX_WORDS. A "word"
    that folds to nothing (just an accent mark) is dropped, because an empty
    word would match every record.
    """
    words = [fold(word) for word in (q or "").split()]
    return [word for word in words if word][:MAX_WORDS]


def contains(column, word):
    """SQL condition: the column contains the (already folded) word."""
    return func.instr(func.fold(column), word) > 0


def all_words_match(columns, q):
    """
    SQL condition: every word appears in at least one of the columns.
    "bank card" finds a record with "card" in the title and "bank" in the text.
    Returns None when there is nothing to search for.
    """
    words = search_words(q)
    if not words:
        return None
    return and_(*[or_(*[contains(column, word) for column in columns]) for word in words])


def find_snippet(text, q, width=70):
    """
    A short piece of text around the first matching word, split into
    (before, match, after) so the page can highlight the match safely.
    Returns None if no word appears in the text.
    """
    text = text or ""
    # Fold one character at a time, remembering where each folded character
    # came from, because folding can change the length ("ß" becomes "ss")
    folded, source = "", []
    for index, char in enumerate(text):
        piece = fold(char)
        folded += piece
        source += [index] * len(piece)

    for word in search_words(q):
        position = folded.find(word)
        if position == -1 or not word:
            continue
        start = source[position]
        end = source[position + len(word) - 1] + 1
        before = text[max(0, start - width):start]
        after = text[end:end + width]
        return (
            ("..." if start > width else "") + before,
            text[start:end],
            after + ("..." if end + width < len(text) else ""),
        )
    return None
