"""
Day 13 - tests for the chat page.

The AI is replaced by fake_ai, so nothing leaves this computer. Tests marked
as using the fallback run the real fallback provider.
"""

import re
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app.forms.chat_forms import MAX_MESSAGE_LENGTH
from app.models import Conversation, Message, User
from app.services.ai_service import FALLBACK_LABEL, AIResponse, AIServiceError
from app.services.chat_service import (
    MAX_HISTORY_MESSAGES,
    build_ai_messages,
    get_latest_conversation,
    is_fallback_message,
    make_title,
)


def get_tester():
    return User.query.filter_by(username="tester").first()


def add_conversation(db, user=None, title="A chat", messages=(), **fields):
    conversation = Conversation(user=user or get_tester(), title=title, **fields)
    start = datetime(2026, 1, 1)
    for number, (role, content) in enumerate(messages):
        conversation.messages.append(
            Message(role=role, content=content, created_at=start + timedelta(minutes=number))
        )
    db.session.add(conversation)
    db.session.commit()
    return conversation


def page(client, path):
    return client.get(path).get_data(as_text=True)


class FakeAI:
    """Stands in for ask_ai(). Records what it was sent and returns a set answer."""

    def __init__(self, text="Fake AI answer", error=None):
        self.text = text
        self.error = error
        self.calls = []

    def __call__(self, messages):
        self.calls.append(messages)
        if self.error:
            raise self.error
        return AIResponse(text=self.text, provider="fake")


@pytest.fixture
def fake_ai(monkeypatch):
    ai = FakeAI()
    monkeypatch.setattr("app.services.chat_service.ask_ai", ai)
    return ai


# ---------- Access ----------

@pytest.mark.parametrize("method, path", [
    ("get", "/chat"),
    ("get", "/chat/new"),
    ("post", "/chat/new"),
    ("get", "/chat/1"),
    ("post", "/chat/1"),
])
def test_every_chat_page_requires_login(client, method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login")


def test_chat_opens_a_new_chat_when_there_are_none(auth_client):
    assert auth_client.get("/chat").headers["Location"] == "/chat/new"
    assert "Ask a question to start" in page(auth_client, "/chat/new")


def test_chat_opens_the_most_recent_chat(db, auth_client):
    add_conversation(db, title="Older", updated_at=datetime(2026, 1, 1))
    newer = add_conversation(db, title="Newer", updated_at=datetime(2026, 2, 1))
    assert auth_client.get("/chat").headers["Location"] == f"/chat/{newer.id}"


def test_opening_a_new_chat_saves_nothing(auth_client):
    auth_client.get("/chat/new")
    assert Conversation.query.count() == 0


def test_menu_links_to_chat_and_highlights_it(auth_client):
    html = page(auth_client, "/chat/new")
    assert re.search(r'nav-link active"\s+href="/chat"', html)


# ---------- Sending messages ----------

def test_first_message_creates_a_conversation_and_saves_both_sides(auth_client, fake_ai):
    response = auth_client.post("/chat/new", data={"message": "  What is Flask?  "})
    conversation = Conversation.query.one()
    assert response.status_code == 302
    assert response.headers["Location"] == f"/chat/{conversation.id}"
    assert conversation.user_id == get_tester().id
    assert conversation.title == "What is Flask?"
    assert [(m.role, m.content) for m in conversation.messages] == [
        ("user", "What is Flask?"),
        ("assistant", "Fake AI answer"),
    ]


def test_message_and_answer_are_shown_on_the_page(auth_client, fake_ai):
    auth_client.post("/chat/new", data={"message": "What is Flask?"})
    html = page(auth_client, f"/chat/{Conversation.query.one().id}")
    assert "What is Flask?" in html
    assert "Fake AI answer" in html


def test_second_message_continues_the_same_conversation(db, auth_client, fake_ai):
    conversation = add_conversation(db, messages=[("user", "One"), ("assistant", "Two")])
    response = auth_client.post(f"/chat/{conversation.id}", data={"message": "Three"})
    assert response.headers["Location"] == f"/chat/{conversation.id}"
    assert Conversation.query.count() == 1
    assert [m.content for m in db.session.get(Conversation, conversation.id).messages] == [
        "One", "Two", "Three", "Fake AI answer",
    ]


def test_sending_a_message_moves_the_chat_to_most_recent(db, auth_client, fake_ai):
    first = add_conversation(db, title="First", updated_at=datetime(2026, 1, 1))
    add_conversation(db, title="Second", updated_at=datetime(2026, 2, 1))
    auth_client.post(f"/chat/{first.id}", data={"message": "Hello"})
    assert get_latest_conversation(get_tester().id).id == first.id


def test_messages_saved_at_the_same_moment_keep_their_order(db, auth_client):
    same_time = datetime(2026, 1, 1)
    conversation = Conversation(user=get_tester(), title="Tie")
    conversation.messages.append(Message(role="user", content="Question", created_at=same_time))
    conversation.messages.append(Message(role="assistant", content="Answer", created_at=same_time))
    db.session.add(conversation)
    db.session.commit()
    db.session.expire_all()
    assert [m.content for m in db.session.get(Conversation, conversation.id).messages] == [
        "Question", "Answer",
    ]


# ---------- Rejected messages ----------

@pytest.mark.parametrize("text, error", [
    ("", "Please enter a message."),
    ("     ", "Please enter a message."),
    ("x" * (MAX_MESSAGE_LENGTH + 1), f"{MAX_MESSAGE_LENGTH} characters or fewer"),
])
def test_invalid_message_is_rejected_without_calling_the_ai(auth_client, fake_ai, text, error):
    response = auth_client.post("/chat/new", data={"message": text})
    assert response.status_code == 200
    assert error in response.get_data(as_text=True)
    assert fake_ai.calls == []
    assert Conversation.query.count() == 0


def test_longest_allowed_message_is_accepted(auth_client, fake_ai):
    assert auth_client.post("/chat/new", data={"message": "x" * MAX_MESSAGE_LENGTH}).status_code == 302


# ---------- When the AI fails ----------

def test_ai_failure_shows_the_error_saves_nothing_and_keeps_the_text(auth_client, monkeypatch):
    monkeypatch.setattr("app.services.chat_service.ask_ai",
                        FakeAI(error=AIServiceError("The AI service is busy.")))
    response = auth_client.post("/chat/new", data={"message": "My unsent question"})
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "The AI service is busy." in html
    assert "alert-danger" in html
    assert "My unsent question" in html
    assert Conversation.query.count() == 0
    assert Message.query.count() == 0


def test_ai_failure_leaves_an_existing_chat_unchanged(db, auth_client, monkeypatch):
    conversation = add_conversation(db, messages=[("user", "One"), ("assistant", "Two")])
    monkeypatch.setattr("app.services.chat_service.ask_ai", FakeAI(error=AIServiceError("Down.")))
    html = auth_client.post(f"/chat/{conversation.id}", data={"message": "Three"}).get_data(as_text=True)
    assert "Down." in html
    assert "One" in html and "Two" in html  # the chat is still on the page
    assert Message.query.count() == 2


def test_the_rest_of_the_app_works_after_an_ai_failure(auth_client, monkeypatch):
    monkeypatch.setattr("app.services.chat_service.ask_ai", FakeAI(error=AIServiceError("Down.")))
    auth_client.post("/chat/new", data={"message": "Hello"})
    assert auth_client.get("/").status_code == 200
    assert auth_client.get("/tasks").status_code == 200


# ---------- What the AI is sent ----------

def test_ai_receives_the_history_and_the_new_message_in_order(db, auth_client, fake_ai):
    conversation = add_conversation(db, messages=[("user", "One"), ("assistant", "Two")])
    auth_client.post(f"/chat/{conversation.id}", data={"message": "Three"})
    assert fake_ai.calls == [[
        {"role": "user", "content": "One"},
        {"role": "assistant", "content": "Two"},
        {"role": "user", "content": "Three"},
    ]]


def test_ai_never_receives_another_chat_or_another_users_data(db, auth_client, make_user, fake_ai):
    add_conversation(db, user=make_user("alice"), messages=[("user", "Alice secret")])
    add_conversation(db, title="My other chat", messages=[("user", "Other chat secret")])
    auth_client.post("/chat/new", data={"message": "Hello"})
    assert fake_ai.calls == [[{"role": "user", "content": "Hello"}]]


def test_fallback_replies_are_never_sent_to_the_ai_as_history(db, auth_client):
    conversation = add_conversation(db, messages=[
        ("user", "One"),
        ("assistant", f"{FALLBACK_LABEL} No AI provider is configured."),
        ("user", "Two"),
        ("assistant", "A real answer"),
    ])
    assert build_ai_messages(conversation, "Three") == [
        {"role": "user", "content": "One"},
        {"role": "user", "content": "Two"},
        {"role": "assistant", "content": "A real answer"},
        {"role": "user", "content": "Three"},
    ]


def test_history_is_limited_and_still_starts_with_a_user_message(db, auth_client):
    pairs = []
    for number in range(MAX_HISTORY_MESSAGES):
        pairs += [("user", f"Q{number}"), ("assistant", f"A{number}")]
    pairs.append(("user", "Q-last"))
    conversation = add_conversation(db, messages=pairs)

    messages = build_ai_messages(conversation, "New")
    assert messages[0]["role"] == "user"
    assert len(messages) <= MAX_HISTORY_MESSAGES + 1
    assert messages[-1] == {"role": "user", "content": "New"}
    assert messages[-2]["content"] == "Q-last"


# ---------- The fallback on the page (real fallback provider) ----------

def test_fallback_mode_is_announced_before_anything_is_sent(auth_client):
    assert "answers here are not from an AI" in page(auth_client, "/chat/new")


def test_no_fallback_notice_when_an_ai_is_set_up(app, auth_client):
    app.config.update(AI_PROVIDER="claude", AI_API_KEY="fake-key-for-tests-only")
    assert "answers here are not from an AI" not in page(auth_client, "/chat/new")


def test_fallback_reply_is_saved_and_marked_not_ai_on_the_page(auth_client):
    auth_client.post("/chat/new", data={"message": "What is the capital of France?"})
    conversation = Conversation.query.one()
    assert is_fallback_message(conversation.messages[1])
    html = page(auth_client, f"/chat/{conversation.id}")
    assert "Not AI" in html
    assert "app-bubble-fallback" in html
    assert FALLBACK_LABEL in html
    assert "Paris" not in html


def test_real_answers_are_not_marked_not_ai(app, db, auth_client):
    app.config.update(AI_PROVIDER="claude", AI_API_KEY="fake-key-for-tests-only")
    conversation = add_conversation(db, messages=[("user", "Hi"), ("assistant", "A real answer")])
    html = page(auth_client, f"/chat/{conversation.id}")
    assert "A real answer" in html
    assert "Not AI" not in html
    assert "app-bubble-fallback" not in html


def test_user_cannot_get_the_not_ai_mark_or_lose_it_by_typing_the_label(db, auth_client):
    conversation = add_conversation(db, messages=[("user", FALLBACK_LABEL)])
    assert is_fallback_message(conversation.messages[0]) is False


# ---------- One user can't reach another user's chats ----------

@pytest.mark.parametrize("method", ["get", "post"])
def test_another_users_chat_gives_404_and_stays_unchanged(db, auth_client, make_user, fake_ai, method):
    conversation = add_conversation(db, user=make_user("alice"), title="Alice private",
                                    messages=[("user", "Alice secret")])
    response = getattr(auth_client, method)(f"/chat/{conversation.id}", data={"message": "Hacked"})
    assert response.status_code == 404
    assert "Alice secret" not in response.get_data(as_text=True)
    assert fake_ai.calls == []
    assert Message.query.count() == 1


def test_chat_never_opens_another_users_latest_chat(db, auth_client, make_user):
    add_conversation(db, user=make_user("alice"), title="Alice private")
    assert auth_client.get("/chat").headers["Location"] == "/chat/new"


def test_form_cannot_choose_the_owner(auth_client, make_user, fake_ai):
    auth_client.post("/chat/new", data={"message": "Hello", "user_id": make_user("alice").id})
    assert Conversation.query.one().user_id == get_tester().id


@pytest.mark.parametrize("path", ["/chat/999", "/chat/99999999999999999999"])
def test_chat_that_does_not_exist_gives_404(auth_client, path):
    assert auth_client.get(path).status_code == 404


# ---------- Titles ----------

@pytest.mark.parametrize("text, expected", [
    ("Short question", "Short question"),
    ("Two\nlines   here", "Two lines here"),
    ("x" * 61, "x" * 60 + "..."),
    ("x" * 60, "x" * 60),
])
def test_make_title(text, expected):
    assert make_title(text) == expected


# ---------- Safety ----------

def test_user_and_ai_text_is_shown_as_text_not_run(auth_client, monkeypatch):
    bad = "<script>alert(1)</script>"
    monkeypatch.setattr("app.services.chat_service.ask_ai", FakeAI(text=bad))
    auth_client.post("/chat/new", data={"message": bad})
    assert bad not in page(auth_client, f"/chat/{Conversation.query.one().id}")


def test_error_message_and_returned_text_are_escaped(auth_client, monkeypatch):
    bad = "<script>alert(1)</script>"
    monkeypatch.setattr("app.services.chat_service.ask_ai", FakeAI(error=AIServiceError("Down.")))
    html = auth_client.post("/chat/new", data={"message": bad}).get_data(as_text=True)
    assert bad not in html


def test_send_cannot_be_triggered_without_a_csrf_token(app, auth_client, fake_ai):
    app.config["WTF_CSRF_ENABLED"] = True
    assert auth_client.post("/chat/new", data={"message": "Hello"}).status_code == 400
    assert fake_ai.calls == []
    assert Conversation.query.count() == 0


def test_real_form_carries_a_working_csrf_token(app, auth_client, fake_ai):
    app.config["WTF_CSRF_ENABLED"] = True
    html = page(auth_client, "/chat/new")
    token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)
    data = {"message": "Hello", "csrf_token": token}
    assert auth_client.post("/chat/new", data=data).status_code == 302


# ---------- The page ----------

def test_page_loads_the_chat_script_and_has_a_real_form(auth_client):
    html = page(auth_client, "/chat/new")
    assert "js/chat.js" in html
    assert 'method="post"' in html
    assert 'id="chat-send"' in html
    assert 'id="chat-status"' in html
    assert (Path(auth_client.application.static_folder) / "js" / "chat.js").exists()


def test_new_chat_button_appears_in_an_existing_chat(db, auth_client):
    conversation = add_conversation(db)
    assert 'href="/chat/new"' in page(auth_client, f"/chat/{conversation.id}")


def test_times_are_shown_in_the_users_time_zone(db, auth_client):
    get_tester().timezone = "Asia/Tokyo"
    conversation = add_conversation(db, messages=[("user", "Hi")])
    assert "Thu 01 Jan 2026, 09:00 JST" in page(auth_client, f"/chat/{conversation.id}")
