"""Day 18 - tests for saved chats: the list, renaming, deleting and how much history the AI sees."""

import re
from datetime import datetime, timedelta

import pytest

from app.models import Conversation, Message, User
from app.services.chat_service import (
    MAX_HISTORY_CHARACTERS,
    MAX_HISTORY_MESSAGES,
    build_ai_messages,
    build_conversation_list,
)
from app.services.common import ITEMS_PER_PAGE


def get_tester():
    return User.query.filter_by(username="tester").first()


def add_chat(db, title="Chat", user=None, messages=(("user", "Q"), ("assistant", "A")), updated_at=None):
    conversation = Conversation(user=user or get_tester(), title=title)
    if updated_at:
        conversation.updated_at = updated_at
    for role, content in messages:
        conversation.messages.append(Message(role=role, content=content))
    db.session.add(conversation)
    db.session.commit()
    return conversation


def page(client, path):
    return client.get(path).get_data(as_text=True)


# ---------- Access ----------

@pytest.mark.parametrize("method, path", [
    ("get", "/chat/history"),
    ("get", "/chat/1/rename"),
    ("post", "/chat/1/rename"),
    ("get", "/chat/1/delete"),
    ("post", "/chat/1/delete"),
])
def test_login_required(client, method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login")


# ---------- The list ----------

def test_list_shows_chats_newest_first_with_message_counts(db, auth_client):
    add_chat(db, "Older chat", updated_at=datetime(2026, 1, 1))
    add_chat(db, "Newer chat", updated_at=datetime(2026, 2, 1),
             messages=[("user", "1"), ("assistant", "2"), ("user", "3"), ("assistant", "4")])
    html = page(auth_client, "/chat/history")
    assert html.index("Newer chat") < html.index("Older chat")
    assert "4 messages" in html
    assert "2 messages" in html
    assert "2 chats" in html


def test_list_query_counts_messages_in_the_database(db, auth_client):
    add_chat(db, "One", messages=[("user", "only")])
    rows = build_conversation_list(get_tester().id).all()
    assert [(conversation.title, count) for conversation, count in rows] == [("One", 1)]


def test_list_shows_only_the_users_own_chats(db, auth_client, make_user):
    add_chat(db, "ALICE-CHAT", user=make_user("alice"))
    add_chat(db, "My chat")
    html = page(auth_client, "/chat/history")
    assert "My chat" in html
    assert "ALICE-CHAT" not in html
    assert "1 chat" in html


def test_empty_list_has_a_message(auth_client):
    assert "You have no saved chats yet." in page(auth_client, "/chat/history")


def test_list_links_open_each_chat(db, auth_client):
    conversation = add_chat(db, "Open me")
    assert f'href="/chat/{conversation.id}"' in page(auth_client, "/chat/history")


def test_long_list_is_split_into_pages(db, auth_client):
    user = get_tester()
    for number in range(ITEMS_PER_PAGE + 1):
        add_chat(db, f"Chat {number}", user=user)
    html = page(auth_client, "/chat/history")
    assert html.count('class="list-group-item app-item"') == ITEMS_PER_PAGE
    assert "Page 1 of 2" in html
    assert page(auth_client, "/chat/history?page=2").count('class="list-group-item app-item"') == 1


@pytest.mark.parametrize("number", ["0", "-1", "999", "99999999999999999999999", "abc"])
def test_bad_page_numbers_are_corrected(db, auth_client, number):
    add_chat(db, "Still shown")
    response = auth_client.get(f"/chat/history?page={number}")
    assert response.status_code == 200
    assert "Still shown" in response.get_data(as_text=True)


def test_chat_page_links_to_the_list_rename_and_delete(db, auth_client):
    conversation = add_chat(db)
    html = page(auth_client, f"/chat/{conversation.id}")
    assert 'href="/chat/history"' in html
    assert f'href="/chat/{conversation.id}/rename"' in html
    assert f'href="/chat/{conversation.id}/delete"' in html
    assert f"remembers the last {MAX_HISTORY_MESSAGES} messages" in html


def test_new_chat_page_links_to_the_list(auth_client):
    assert 'href="/chat/history"' in page(auth_client, "/chat/new")


def test_menu_highlights_chat_on_the_list(auth_client):
    assert re.search(r'nav-link active"\s+href="/chat"', page(auth_client, "/chat/history"))


# ---------- Rename ----------

def test_rename_form_is_filled_in(db, auth_client):
    conversation = add_chat(db, "Old name")
    assert 'value="Old name"' in page(auth_client, f"/chat/{conversation.id}/rename")


def test_rename_saves_the_new_name(db, auth_client):
    conversation = add_chat(db, "Old name")
    response = auth_client.post(f"/chat/{conversation.id}/rename", data={"title": "  Exam revision  "})
    assert response.headers["Location"] == f"/chat/{conversation.id}"
    assert db.session.get(Conversation, conversation.id).title == "Exam revision"


@pytest.mark.parametrize("title, message", [
    ("", "Enter a name for the chat."),
    ("   ", "Enter a name for the chat."),
    ("x" * 201, "200 characters or fewer"),
])
def test_invalid_name_is_refused(db, auth_client, title, message):
    conversation = add_chat(db, "Old name")
    response = auth_client.post(f"/chat/{conversation.id}/rename", data={"title": title})
    assert message in response.get_data(as_text=True)
    assert db.session.get(Conversation, conversation.id).title == "Old name"


def test_name_with_html_is_shown_as_text(db, auth_client):
    conversation = add_chat(db)
    bad = "<script>alert(1)</script>"
    auth_client.post(f"/chat/{conversation.id}/rename", data={"title": bad})
    for path in ("/chat/history", f"/chat/{conversation.id}", f"/chat/{conversation.id}/delete"):
        assert bad not in page(auth_client, path)


# ---------- Delete ----------

def test_get_only_asks_and_post_deletes_the_chat_and_its_messages(db, auth_client):
    removed_id = add_chat(db, "Remove me").id
    kept_id = add_chat(db, "Keep me").id
    html = page(auth_client, f"/chat/{removed_id}/delete")
    assert 'Delete "Remove me"?' in html
    assert "All of its messages will be deleted too." in html
    assert Conversation.query.count() == 2

    response = auth_client.post(f"/chat/{removed_id}/delete")
    assert response.headers["Location"] == "/chat/history"
    assert db.session.get(Conversation, removed_id) is None
    assert Message.query.filter_by(conversation_id=removed_id).count() == 0
    assert db.session.get(Conversation, kept_id) is not None
    assert Message.query.filter_by(conversation_id=kept_id).count() == 2


def test_after_deleting_the_latest_chat_chat_opens_the_next_one(db, auth_client):
    older = add_chat(db, "Older", updated_at=datetime(2026, 1, 1))
    newer = add_chat(db, "Newer", updated_at=datetime(2026, 2, 1))
    auth_client.post(f"/chat/{newer.id}/delete")
    assert auth_client.get("/chat").headers["Location"] == f"/chat/{older.id}"


def test_deleting_the_last_chat_leads_to_a_new_one(db, auth_client):
    conversation = add_chat(db)
    auth_client.post(f"/chat/{conversation.id}/delete")
    assert auth_client.get("/chat").headers["Location"] == "/chat/new"


# ---------- One user can't reach another user's chats ----------

@pytest.mark.parametrize("method, action", [
    ("get", "rename"),
    ("post", "rename"),
    ("get", "delete"),
    ("post", "delete"),
])
def test_another_users_chat_gives_404_and_stays_unchanged(db, auth_client, make_user, method, action):
    conversation = add_chat(db, "ALICE-CHAT", user=make_user("alice"))
    response = getattr(auth_client, method)(f"/chat/{conversation.id}/{action}", data={"title": "Hacked"})
    assert response.status_code == 404
    assert "ALICE-CHAT" not in response.get_data(as_text=True)
    assert db.session.get(Conversation, conversation.id).title == "ALICE-CHAT"
    assert Message.query.filter_by(conversation_id=conversation.id).count() == 2


@pytest.mark.parametrize("path", ["/chat/999/rename", "/chat/99999999999999999999/delete"])
def test_chat_that_does_not_exist_gives_404(auth_client, path):
    assert auth_client.get(path).status_code == 404


# ---------- CSRF ----------

@pytest.mark.parametrize("action", ["rename", "delete"])
def test_changes_need_a_csrf_token(app, db, auth_client, action):
    conversation = add_chat(db, "Protected")
    app.config["WTF_CSRF_ENABLED"] = True
    assert auth_client.post(f"/chat/{conversation.id}/{action}", data={"title": "Hacked"}).status_code == 400
    assert db.session.get(Conversation, conversation.id).title == "Protected"


def test_delete_form_carries_a_working_csrf_token(app, db, auth_client):
    conversation = add_chat(db)
    app.config["WTF_CSRF_ENABLED"] = True
    html = page(auth_client, f"/chat/{conversation.id}/delete")
    token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
    assert auth_client.post(f"/chat/{conversation.id}/delete", data={"csrf_token": token}).status_code == 302
    assert Conversation.query.count() == 0


# ---------- How much history the AI sees ----------

def test_long_history_is_cut_by_size_keeping_the_newest(db, auth_client):
    big = "x" * (MAX_HISTORY_CHARACTERS // 3)
    conversation = add_chat(db, messages=[
        ("user", "OLDEST " + big), ("assistant", "A1 " + big),
        ("user", "Q2 " + big), ("assistant", "A2 " + big),
    ])
    messages = build_ai_messages(conversation, "New question")
    total = sum(len(m["content"]) for m in messages[:-1])
    assert total <= MAX_HISTORY_CHARACTERS
    assert not any(m["content"].startswith("OLDEST") for m in messages)
    assert messages[0]["role"] == "user"
    assert messages[-1] == {"role": "user", "content": "New question"}


def test_short_history_is_sent_in_full(db, auth_client):
    conversation = add_chat(db, messages=[("user", "One"), ("assistant", "Two")])
    assert [m["content"] for m in build_ai_messages(conversation, "Three")] == ["One", "Two", "Three"]


def test_one_huge_old_message_does_not_block_the_new_one(db, auth_client):
    conversation = add_chat(db, messages=[("user", "x" * (MAX_HISTORY_CHARACTERS + 10)),
                                          ("assistant", "short")])
    messages = build_ai_messages(conversation, "New")
    assert messages == [{"role": "user", "content": "New"}]


def test_chats_are_kept_separate(db, auth_client, monkeypatch):
    from app.services.ai_service import AIResponse

    calls = []
    monkeypatch.setattr("app.services.chat_service.ask_ai",
                        lambda messages: calls.append(messages) or AIResponse("ok", "fake"))
    first = add_chat(db, "First", messages=[("user", "FIRST-CHAT-SECRET"), ("assistant", "ok")])
    second = add_chat(db, "Second", messages=[("user", "Hello"), ("assistant", "Hi")])
    auth_client.post(f"/chat/{second.id}", data={"message": "Next"})
    assert "FIRST-CHAT-SECRET" not in str(calls)
    assert first.id != second.id
