"""Day 11 - tests for the notes module and search."""

import re
from datetime import datetime, timedelta

import pytest

from app.models import Note, User
from app.services.common import ITEMS_PER_PAGE
from app.services.note_service import (
    MAX_SEARCH_LENGTH,
    build_note_query,
    clean_search_text,
    get_user_categories,
)


def get_tester():
    return User.query.filter_by(username="tester").first()


def add_note(db, user=None, **fields):
    fields.setdefault("title", "A note")
    note = Note(user=user or get_tester(), **fields)
    db.session.add(note)
    db.session.commit()
    return note


def post_note(client, path="/notes/new", **overrides):
    data = {"title": "Flask notes", "content": "", "category": ""}
    data.update(overrides)
    return client.post(path, data=data)


def page(client, path="/notes"):
    return client.get(path).get_data(as_text=True)


def search(user, q=None, category=None):
    return [note.title for note in build_note_query(user.id, q=q, category=category).all()]


# ---------- Login required ----------

@pytest.mark.parametrize("method, path", [
    ("get", "/notes"),
    ("get", "/notes/new"),
    ("post", "/notes/new"),
    ("get", "/notes/1"),
    ("get", "/notes/1/edit"),
    ("post", "/notes/1/edit"),
    ("get", "/notes/1/delete"),
    ("post", "/notes/1/delete"),
])
def test_every_note_page_requires_login(client, method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login")


# ---------- Create and view ----------

def test_create_note_and_go_to_it(auth_client):
    response = post_note(auth_client, title="  Flask notes ", content="Blueprints", category="Study")
    note = Note.query.one()
    assert response.status_code == 302
    assert response.headers["Location"] == f"/notes/{note.id}"
    assert note.user_id == get_tester().id
    assert note.title == "Flask notes"
    assert note.content == "Blueprints"
    assert note.category == "Study"


def test_note_with_only_a_title(auth_client):
    post_note(auth_client)
    note = Note.query.one()
    assert note.content == ""
    assert note.category is None
    assert "This note has no content." in page(auth_client, f"/notes/{note.id}")


@pytest.mark.parametrize("overrides, message", [
    ({"title": ""}, "Enter a title."),
    ({"title": "    "}, "Enter a title."),
    ({"title": "x" * 201}, "200 characters or fewer"),
    ({"content": "x" * 50001}, "50000 characters or fewer"),
    ({"category": "x" * 51}, "50 characters or fewer"),
])
def test_invalid_note_is_rejected(auth_client, overrides, message):
    response = post_note(auth_client, **overrides)
    assert response.status_code == 200
    assert message in response.get_data(as_text=True)
    assert Note.query.count() == 0


def test_form_cannot_set_the_owner(auth_client, make_user):
    post_note(auth_client, user_id=make_user("alice").id)
    assert Note.query.one().user_id == get_tester().id


def test_view_shows_all_of_a_long_note_with_its_line_breaks(db, auth_client):
    long_text = "First line\nSecond line\n" + "word " * 500 + "THE-END"
    note = add_note(db, content=long_text)
    html = page(auth_client, f"/notes/{note.id}")
    assert "First line\nSecond line" in html
    assert "THE-END" in html
    assert "app-note-content" in html


def test_list_shortens_a_long_note(db, auth_client):
    add_note(db, content="word " * 500 + "THE-END")
    assert "THE-END" not in page(auth_client)


# ---------- Edit ----------

def test_edit_form_is_filled_with_saved_values(db, auth_client):
    note = add_note(db, title="Original", content="Details", category="Home")
    html = page(auth_client, f"/notes/{note.id}/edit")
    assert 'value="Original"' in html
    assert "Details" in html
    assert 'value="Home"' in html


def test_edit_saves_changes_and_can_clear_fields(db, auth_client):
    note = add_note(db, title="Original", content="Details", category="Home")
    response = post_note(auth_client, f"/notes/{note.id}/edit", title="Changed")
    assert response.headers["Location"] == f"/notes/{note.id}"
    note = db.session.get(Note, note.id)
    assert note.title == "Changed"
    assert note.content == ""
    assert note.category is None


def test_invalid_edit_changes_nothing(db, auth_client):
    note = add_note(db, title="Original")
    response = post_note(auth_client, f"/notes/{note.id}/edit", title="")
    assert "Enter a title." in response.get_data(as_text=True)
    assert db.session.get(Note, note.id).title == "Original"


def test_editing_moves_a_note_to_the_top(db, auth_client):
    old = datetime(2026, 1, 1)
    first = add_note(db, title="First", updated_at=old)
    add_note(db, title="Second", updated_at=old + timedelta(days=1))
    post_note(auth_client, f"/notes/{first.id}/edit", title="First edited")
    assert search(get_tester())[0] == "First edited"


def test_saving_without_changes_keeps_the_edited_time(db, auth_client):
    old = datetime(2026, 1, 1)
    note = add_note(db, title="Same", content="Text", updated_at=old)
    post_note(auth_client, f"/notes/{note.id}/edit", title="Same", content="Text")
    assert db.session.get(Note, note.id).updated_at == old


# ---------- Delete ----------

def test_get_only_asks_and_post_deletes(db, auth_client):
    note = add_note(db, title="Remove me")
    assert 'Delete "Remove me"?' in page(auth_client, f"/notes/{note.id}/delete")
    assert Note.query.count() == 1

    response = auth_client.post(f"/notes/{note.id}/delete")
    assert response.headers["Location"] == "/notes"
    assert Note.query.count() == 0


# ---------- One user can't reach another user's notes ----------

@pytest.mark.parametrize("method, suffix", [
    ("get", ""),
    ("get", "/edit"),
    ("post", "/edit"),
    ("get", "/delete"),
    ("post", "/delete"),
])
def test_another_users_note_gives_404_and_stays_unchanged(db, auth_client, make_user, method, suffix):
    note = add_note(db, user=make_user("alice"), title="Alice private", content="Secret")
    response = getattr(auth_client, method)(f"/notes/{note.id}{suffix}", data={"title": "Hacked"})
    assert response.status_code == 404
    assert "Alice private" not in response.get_data(as_text=True)

    note = db.session.get(Note, note.id)
    assert note.title == "Alice private"
    assert note.content == "Secret"


@pytest.mark.parametrize("path", [
    "/notes",
    "/notes?q=Secret",
    "/notes?q=Alice",
    "/notes?category=AliceCategory",
    "/notes/new",
])
def test_lists_searches_and_suggestions_never_show_another_users_notes(db, auth_client, make_user, path):
    add_note(db, user=make_user("alice"), title="Alice private", content="Secret",
             category="AliceCategory")
    add_note(db, title="My note", category="Mine")
    html = page(auth_client, path)
    assert "Alice private" not in html
    assert "AliceCategory</option>" not in html
    assert '<option value="AliceCategory"></option>' not in html


@pytest.mark.parametrize("path", ["/notes/999", "/notes/99999999999999999999"])
def test_id_that_does_not_exist_gives_404(auth_client, path):
    assert auth_client.get(path).status_code == 404


# ---------- Search ----------

@pytest.fixture
def notes(db, auth_client):
    old = datetime(2026, 1, 1)
    add_note(db, title="Bank card", content="Call about the PIN", category="Money", updated_at=old)
    add_note(db, title="Shopping", content="Milk and bread", category="Home",
             updated_at=old + timedelta(days=1))
    add_note(db, title="Exam topics", content="the card game chapter", category="Study",
             updated_at=old + timedelta(days=2))
    return get_tester()


@pytest.mark.parametrize("q, expected", [
    (None, ["Exam topics", "Shopping", "Bank card"]),
    ("", ["Exam topics", "Shopping", "Bank card"]),
    ("shopping", ["Shopping"]),          # in the title, ignoring case
    ("MILK", ["Shopping"]),              # in the content
    ("money", ["Bank card"]),            # in the category
    ("card", ["Exam topics", "Bank card"]),
    ("pin bank", ["Bank card"]),         # every word must match, in any field and order
    ("card money", ["Bank card"]),
    ("milk bank", []),                   # both words exist, but not in one note
    ("nothing-like-this", []),
])
def test_search(notes, q, expected):
    assert search(notes, q) == expected


def test_search_and_category_work_together(notes):
    assert search(notes, "card", "Study") == ["Exam topics"]
    assert search(notes, "milk", "Study") == []


@pytest.mark.parametrize("q, expected", [
    ("100%", ["100% done"]),
    ("%", ["100% done"]),
    ("a_b", ["a_b file"]),
    ("_", ["a_b file"]),
])
def test_wildcard_characters_are_searched_as_plain_text(db, auth_client, q, expected):
    add_note(db, title="100% done")
    add_note(db, title="100 apples")
    add_note(db, title="a_b file")
    add_note(db, title="axb file")
    assert search(get_tester(), q) == expected


def test_search_with_sql_text_is_harmless(notes, auth_client):
    response = auth_client.get("/notes", query_string={"q": "'; DROP TABLE notes; --"})
    assert response.status_code == 200
    assert Note.query.count() == 3


@pytest.mark.parametrize("text, expected", [
    (None, ""),
    ("", ""),
    ("    ", ""),
    ("  bank    card ", "bank card"),
    ("x" * 500, "x" * MAX_SEARCH_LENGTH),
])
def test_clean_search_text(text, expected):
    assert clean_search_text(text) == expected


def test_search_page_shows_results_and_keeps_the_text(notes, auth_client):
    html = page(auth_client, "/notes?q=milk")
    assert "Shopping" in html
    assert "Bank card" not in html
    assert 'value="milk"' in html
    assert "1 note matches" in html


def test_only_spaces_counts_as_no_search(notes, auth_client):
    html = page(auth_client, "/notes?q=%20%20")
    assert "3 notes" in html
    assert "match" not in html.split("Search notes")[0].split('role="status"')[1]


def test_search_with_no_results_shows_a_message(notes, auth_client):
    assert 'No notes match "zebra".' in page(auth_client, "/notes?q=zebra")


def test_category_filter_on_the_page(notes, auth_client):
    html = page(auth_client, "/notes?category=Home")
    assert "Shopping" in html
    assert "Bank card" not in html
    assert re.search(r'<option value="Home" selected>', html)


def test_categories_are_unique_and_sorted(db, auth_client):
    for category in ("Work", "Home", "Work", None):
        add_note(db, category=category)
    assert get_user_categories(get_tester().id) == ["Home", "Work"]


# ---------- Pages ----------

def test_long_lists_are_split_into_pages_and_keep_the_search(db, auth_client):
    user = get_tester()
    db.session.add_all([Note(user=user, title=f"Match {n}") for n in range(ITEMS_PER_PAGE + 1)])
    db.session.commit()

    html = page(auth_client, "/notes?q=match")
    assert html.count('class="list-group-item app-item"') == ITEMS_PER_PAGE
    assert "Page 1 of 2" in html
    assert "page=2" in html and "q=match" in html

    html = page(auth_client, "/notes?q=match&page=2")
    assert html.count('class="list-group-item app-item"') == 1


@pytest.mark.parametrize("number", ["0", "-5", "999", "99999999999999999999999", "abc"])
def test_bad_page_numbers_are_corrected(db, auth_client, number):
    add_note(db, title="Still shown")
    response = auth_client.get(f"/notes?page={number}")
    assert response.status_code == 200
    assert "Still shown" in response.get_data(as_text=True)


# ---------- Display, dashboard and safety ----------

def test_new_user_sees_the_empty_message(auth_client):
    assert "You have no notes yet." in page(auth_client)


def test_edited_time_is_shown_in_the_users_time_zone(db, auth_client):
    get_tester().timezone = "Asia/Tokyo"
    add_note(db, updated_at=datetime(2099, 1, 15, 12, 0))
    assert "Thu 15 Jan 2099, 21:00 JST" in page(auth_client)


def test_user_text_is_shown_as_text_not_run(auth_client):
    bad = "<script>alert(1)</script>"
    post_note(auth_client, title=bad, content=bad, category=bad)
    note = Note.query.one()
    paths = ("/notes", "/", f"/notes/{note.id}", f"/notes/{note.id}/edit", f"/notes/{note.id}/delete")
    for path in paths:
        assert bad not in page(auth_client, path)


def test_search_text_is_shown_as_text_not_run(auth_client):
    html = auth_client.get("/notes", query_string={"q": "<script>alert(1)</script>"}).get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html


def test_menu_links_to_notes_and_highlights_it(auth_client):
    html = page(auth_client, "/notes/new")
    assert re.search(r'nav-link active"\s+href="/notes"', html)


def test_dashboard_links_to_the_note_and_the_list(db, auth_client):
    note = add_note(db, title="On the dashboard")
    html = page(auth_client, "/")
    assert f'href="/notes/{note.id}"' in html
    assert 'href="/notes"' in html


# ---------- CSRF ----------

@pytest.mark.parametrize("action", ["edit", "delete"])
def test_changes_without_csrf_token_are_rejected(app, db, auth_client, action):
    note = add_note(db, title="Protected")
    app.config["WTF_CSRF_ENABLED"] = True
    assert auth_client.post(f"/notes/{note.id}/{action}", data={"title": "Hacked"}).status_code == 400
    assert db.session.get(Note, note.id).title == "Protected"


def test_real_form_carries_a_working_csrf_token(app, db, auth_client):
    note = add_note(db)
    app.config["WTF_CSRF_ENABLED"] = True
    html = page(auth_client, f"/notes/{note.id}/delete")
    token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
    assert auth_client.post(f"/notes/{note.id}/delete", data={"csrf_token": token}).status_code == 302
    assert Note.query.count() == 0
