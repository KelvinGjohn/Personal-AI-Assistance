"""Day 20 - tests for global search, and for ignoring case and accents."""

import re
from datetime import datetime, timedelta

import pytest

from app.models import Conversation, Message, Note, Reminder, Task, User
from app.services.note_service import build_note_query
from app.services.search_service import PREVIEW_COUNT, SINGLE_TYPE_COUNT, search
from app.text_search import MAX_WORDS, find_snippet, fold, search_words


@pytest.fixture(autouse=True)
def request_context(app):
    """search() builds links with url_for(), which needs a request, as it has on a real page."""
    with app.test_request_context():
        yield


def get_tester():
    return User.query.filter_by(username="tester").first()


def add(db, *records):
    db.session.add_all(records)
    db.session.commit()


def add_chat(db, title, messages, user=None):
    conversation = Conversation(user=user or get_tester(), title=title)
    for role, content in messages:
        conversation.messages.append(Message(role=role, content=content))
    add(db, conversation)
    return conversation


def results(user, q, only_type=""):
    """{type: [titles]} for a search."""
    groups = search(user.id, q, only_type, lambda value: value.strftime("%d %b"))
    return {group.type: [result.title for result in group.results] for group in groups}


def page(client, path):
    return client.get(path).get_data(as_text=True)


# ---------- Folding: case and accents ----------

@pytest.mark.parametrize("text, expected", [
    ("Café", "cafe"),
    ("CAFÉ", "cafe"),
    ("café", "cafe"),
    ("Straße", "strasse"),
    ("ÉCOLE", "ecole"),
    ("naïve résumé", "naive resume"),
    ("Mañana", "manana"),
    ("100% done_ok", "100% done_ok"),
    ("", ""),
    (None, None),
])
def test_fold(text, expected):
    assert fold(text) == expected


def test_search_words_are_folded_limited_and_never_empty():
    assert search_words("  CAFÉ  Bank ") == ["cafe", "bank"]
    assert search_words("́") == []  # only an accent mark
    assert len(search_words(" ".join(f"w{n}" for n in range(30)))) == MAX_WORDS
    assert search_words(None) == []


@pytest.mark.parametrize("q", ["café", "CAFÉ", "cafe", "Cafe", "CAFE"])
def test_accents_and_case_are_ignored(db, auth_client, q):
    add(db, Note(user=get_tester(), title="Café plans"))
    assert results(get_tester(), q)["notes"] == ["Café plans"]


def test_day_11_limit_is_fixed_on_the_notes_page(db, auth_client):
    user = get_tester()
    add(db, Note(user=user, title="Café plans"), Note(user=user, title="École visit"))
    assert [n.title for n in build_note_query(user.id, q="CAFÉ")] == ["Café plans"]
    assert "École visit" in page(auth_client, "/notes?q=ecole")


@pytest.mark.parametrize("q, expected", [
    ("100%", ["100% done"]),
    ("%", ["100% done"]),
    ("a_b", ["a_b file"]),
    ("_", ["a_b file"]),
])
def test_percent_and_underscore_are_plain_characters(db, auth_client, q, expected):
    user = get_tester()
    add(db, Note(user=user, title="100% done"), Note(user=user, title="100 apples"),
        Note(user=user, title="a_b file"), Note(user=user, title="axb file"))
    assert results(user, q)["notes"] == expected


# ---------- What is searched ----------

@pytest.fixture
def everything(db, auth_client):
    user = get_tester()
    add(db,
        Task(user=user, title="Submit report", description="Chapter on the bank loan", category="Uni"),
        Task(user=user, title="Buy milk", category="Home"),
        Reminder(user=user, title="Call the bank", remind_at=datetime(2099, 1, 1), description="About the card"),
        Note(user=user, title="Money", content="Bank card PIN reminder", category="Finance"),
        Note(user=user, title="Recipes", content="Pancakes"))
    add_chat(db, "Study help", [("user", "Explain bank interest"), ("assistant", "Interest is...")])
    add_chat(db, "Holiday", [("user", "Beaches"), ("assistant", "Try the coast")])
    return user


def test_one_search_finds_every_type(everything):
    assert results(everything, "bank") == {
        "tasks": ["Submit report"],
        "reminders": ["Call the bank"],
        "notes": ["Money"],
        "chats": ["Study help"],
    }


@pytest.mark.parametrize("q, kind, expected", [
    ("uni", "tasks", ["Submit report"]),            # task category
    ("card", "reminders", ["Call the bank"]),        # reminder description
    ("finance", "notes", ["Money"]),                 # note category
    ("pancakes", "notes", ["Recipes"]),              # note content
    ("holiday", "chats", ["Holiday"]),               # chat title
    ("coast", "chats", ["Holiday"]),                 # an assistant message
])
def test_each_field_is_searched(everything, q, kind, expected):
    assert results(everything, q)[kind] == expected


def test_every_word_must_match_but_in_any_field(everything):
    assert results(everything, "bank pin")["notes"] == ["Money"]
    assert results(everything, "milk home")["tasks"] == ["Buy milk"]
    assert results(everything, "milk bank")["tasks"] == []


def test_chat_words_can_match_different_messages(db, auth_client):
    add_chat(db, "Mixed", [("user", "alpha"), ("assistant", "beta")])
    assert results(get_tester(), "alpha beta")["chats"] == ["Mixed"]


def test_chat_appears_once_even_if_many_messages_match(db, auth_client):
    add_chat(db, "Repeats", [("user", "bank"), ("assistant", "bank"), ("user", "bank again")])
    group = search(get_tester().id, "bank", "chats", str)[0]
    assert group.total == 1
    assert [r.title for r in group.results] == ["Repeats"]


def test_type_filter_searches_only_that_type(everything):
    assert results(everything, "bank", "notes") == {"notes": ["Money"]}


def test_unknown_type_searches_everything(everything, auth_client):
    html = page(auth_client, "/search?q=bank&type=passwords")
    assert "4 results" in html


def test_empty_search_returns_nothing(everything):
    assert search(everything.id, "   ", "", str) == []


# ---------- Only the user's own records ----------

def test_another_users_records_are_never_found(db, auth_client, make_user):
    alice = make_user("alice")
    add(db,
        Task(user=alice, title="ALICE bank task"),
        Reminder(user=alice, title="ALICE bank reminder", remind_at=datetime(2099, 1, 1)),
        Note(user=alice, title="ALICE bank note"))
    add_chat(db, "ALICE bank chat", [("user", "bank")], user=alice)
    found = results(get_tester(), "bank")
    assert all(titles == [] for titles in found.values())
    assert "ALICE" not in page(auth_client, "/search?q=alice")


# ---------- Limits and counts ----------

def test_everything_view_shows_a_preview_and_a_link_to_all(db, auth_client):
    user = get_tester()
    add(db, *[Note(user=user, title=f"Match {n}") for n in range(PREVIEW_COUNT + 2)])
    group = search(user.id, "match", "", str)[2]
    assert group.total == PREVIEW_COUNT + 2
    assert len(group.results) == PREVIEW_COUNT
    assert "Show all 7" in page(auth_client, "/search?q=match")
    assert "type=notes" in page(auth_client, "/search?q=match")


def test_one_type_shows_up_to_the_larger_limit(db, auth_client):
    user = get_tester()
    add(db, *[Note(user=user, title=f"Match {n}") for n in range(SINGLE_TYPE_COUNT + 1)])
    group = search(user.id, "match", "notes", str)[0]
    assert len(group.results) == SINGLE_TYPE_COUNT
    assert f"Showing the first {SINGLE_TYPE_COUNT}" in page(auth_client, "/search?q=match&type=notes")


# ---------- Snippets ----------

def test_snippet_finds_the_word_ignoring_accents_and_case():
    assert find_snippet("Meet at the Café at noon", "cafe") == ("Meet at the ", "Café", " at noon")


def test_snippet_handles_letters_that_fold_to_two():
    before, match, after = find_snippet("Die Straße ist lang", "strasse")
    assert match == "Straße"
    assert before == "Die " and after == " ist lang"


def test_snippet_is_shortened_around_the_match():
    before, match, after = find_snippet("a" * 200 + " needle " + "b" * 200, "needle", width=20)
    assert match == "needle"
    assert before.startswith("...") and after.endswith("...")
    assert len(before) <= 23 and len(after) <= 23


def test_no_snippet_when_the_word_is_not_in_the_text():
    assert find_snippet("nothing here", "bank") is None
    assert find_snippet(None, "bank") is None


# ---------- The page ----------

@pytest.mark.parametrize("path", ["/search", "/search?q=bank"])
def test_login_required(client, path):
    response = client.get(path)
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login")


def test_page_without_a_search_shows_a_hint(auth_client):
    html = page(auth_client, "/search")
    assert "accents don&#39;t matter" in html or "accents don't matter" in html


def test_results_link_to_each_record(everything, auth_client):
    html = page(auth_client, "/search?q=bank")
    task = Task.query.filter_by(title="Submit report").one()
    note = Note.query.filter_by(title="Money").one()
    chat = Conversation.query.filter_by(title="Study help").one()
    reminder = Reminder.query.one()
    for link in (f"/tasks/{task.id}/edit", f"/notes/{note.id}", f"/chat/{chat.id}",
                 f"/reminders/{reminder.id}/edit"):
        assert f'href="{link}"' in html
    assert "<mark>bank</mark>" in html or "<mark>Bank</mark>" in html


def test_search_text_and_type_are_kept_in_the_form(everything, auth_client):
    html = page(auth_client, "/search?q=bank&type=notes")
    assert 'value="bank"' in html
    assert re.search(r'<option value="notes" selected>', html)


def test_no_results_message(auth_client):
    html = page(auth_client, "/search?q=zebra")
    assert "0 results" in html
    assert "No notes match." in html


def test_html_in_the_search_and_records_is_shown_as_text(db, auth_client):
    bad = "<script>alert(1)</script>"
    add(db, Note(user=get_tester(), title=bad, content=f"x {bad} y"))
    html = auth_client.get("/search", query_string={"q": bad}).get_data(as_text=True)
    assert bad not in html
    assert "&lt;script&gt;" in html


def test_sql_text_in_the_search_is_harmless(everything, auth_client):
    response = auth_client.get("/search", query_string={"q": "'; DROP TABLE notes; --"})
    assert response.status_code == 200
    assert Note.query.count() == 2


def test_very_long_search_is_cut(auth_client):
    assert auth_client.get("/search", query_string={"q": "x" * 5000}).status_code == 200


def test_menu_links_to_search(auth_client):
    assert re.search(r'nav-link active"\s+href="/search"', page(auth_client, "/search"))


def test_dates_are_shown_in_the_users_time_zone(db, auth_client):
    user = get_tester()
    user.timezone = "Asia/Tokyo"
    add(db, Reminder(user=user, title="Late call", remind_at=datetime(2099, 1, 15, 22, 0)))
    assert "Fri 16 Jan 2099, 07:00 JST" in page(auth_client, "/search?q=late")
