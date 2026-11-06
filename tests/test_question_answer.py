"""Day 14 - tests for formatted answers and chat error handling."""

from datetime import timedelta

import pytest

from app.formatting import render_markdown
from app.models import Conversation, Message, User
from app.services.ai_service import FALLBACK_LABEL, SYSTEM_PROMPT, AIResponse, AIServiceError
from app.services.chat_service import (
    CUT_OFF_NOTE,
    MESSAGE_LIMIT,
    MESSAGE_LIMIT_PERIOD,
    count_recent_messages,
)
from app.utils import utc_now


def get_tester():
    return User.query.filter_by(username="tester").first()


def html_of(text):
    return str(render_markdown(text))


class FakeAI:
    def __init__(self, text="Fake answer", error=None, is_cut_off=False):
        self.text = text
        self.error = error
        self.is_cut_off = is_cut_off
        self.calls = 0

    def __call__(self, messages):
        self.calls += 1
        if self.error:
            raise self.error
        return AIResponse(text=self.text, provider="fake", is_cut_off=self.is_cut_off)


def use_ai(monkeypatch, **kwargs):
    ai = FakeAI(**kwargs)
    monkeypatch.setattr("app.services.chat_service.ask_ai", ai)
    return ai


def add_chat(db, messages, user=None):
    conversation = Conversation(user=user or get_tester(), title="Chat")
    for role, content in messages:
        conversation.messages.append(Message(role=role, content=content))
    db.session.add(conversation)
    db.session.commit()
    return conversation


# ---------- Markdown becomes formatted HTML ----------

@pytest.mark.parametrize("text, expected", [
    ("**bold**", "<strong>bold</strong>"),
    ("*italic*", "<em>italic</em>"),
    ("- one\n- two", "<li>one</li>"),
    ("1. first\n2. second", "<ol>"),
    ("Use `pip install`", "<code>pip install</code>"),
    ("```python\nif a < b:\n    pass\n```", "<pre><code>if a &lt; b:\n    pass\n</code></pre>"),
    ("| A | B |\n|---|---|\n| 1 | 2 |", "<td>1</td>"),
    ("## Heading", "<h2>Heading</h2>"),
    ("> quoted", "<blockquote>"),
    ("line one\nline two", "line one<br>"),
])
def test_markdown_is_formatted(text, expected):
    assert expected in html_of(text)


def test_safe_web_link_is_kept_and_cannot_reach_back_to_this_page():
    html = html_of("[Flask docs](https://flask.palletsprojects.com/)")
    assert 'href="https://flask.palletsprojects.com/"' in html
    assert 'rel="noopener noreferrer nofollow"' in html


@pytest.mark.parametrize("text, forbidden", [
    ("<script>alert(1)</script>", "<script"),
    ("<script>alert(1)</script>", "alert(1)"),
    ("<style>body{display:none}</style>", "<style"),
    ("<img src=x onerror=alert(1)>", "<img"),
    ("![tracker](https://evil.example/pixel.png)", "<img"),
    ("<b onclick='alert(1)'>hi</b>", "onclick"),
    ("[click](javascript:alert(1))", "javascript:"),
    ("<a href='javascript:alert(1)'>x</a>", "javascript:"),
    ("<a href='data:text/html,<script>alert(1)</script>'>x</a>", "data:"),
    ("<iframe src='https://evil.example'></iframe>", "<iframe"),
    ("<form action='/logout' method='post'><button>Go</button></form>", "<form"),
    ("[log out](/logout)", 'href="/logout"'),
    ("<div style='position:fixed'>cover</div>", "style="),
    ("<!-- hidden note -->", "hidden note"),
])
def test_dangerous_content_is_removed(text, forbidden):
    assert forbidden not in html_of(text)


def test_text_of_removed_tags_is_kept_where_harmless():
    assert "hi" in html_of("<b onclick='x'>hi</b>")


def test_empty_answer_renders_as_nothing():
    assert html_of("") == ""
    assert html_of(None) == ""


# ---------- What is formatted on the page ----------

def test_ai_answers_are_formatted_on_the_page(db, auth_client):
    conversation = add_chat(db, [("user", "Hi"), ("assistant", "**Formatted** answer")])
    html = auth_client.get(f"/chat/{conversation.id}").get_data(as_text=True)
    assert "<strong>Formatted</strong> answer" in html
    assert "app-markdown" in html


def test_user_messages_are_never_formatted(db, auth_client):
    conversation = add_chat(db, [("user", "**not bold** <b>tag</b>"), ("assistant", "ok")])
    html = auth_client.get(f"/chat/{conversation.id}").get_data(as_text=True)
    assert "**not bold** &lt;b&gt;tag&lt;/b&gt;" in html
    assert "<strong>not bold</strong>" not in html


def test_fallback_replies_stay_plain_text(db, auth_client):
    conversation = add_chat(db, [("user", "Hi"), ("assistant", f"{FALLBACK_LABEL} **x**")])
    html = auth_client.get(f"/chat/{conversation.id}").get_data(as_text=True)
    assert "**x**" in html
    assert "<strong>x</strong>" not in html


def test_harmful_ai_answer_cannot_run_on_the_page(db, auth_client):
    answer = "Here: <script>alert('stolen')</script><img src=x onerror=alert(1)> [x](javascript:alert(1))"
    conversation = add_chat(db, [("user", "Hi"), ("assistant", answer)])
    html = auth_client.get(f"/chat/{conversation.id}").get_data(as_text=True)
    assert "alert('stolen')" not in html
    assert "onerror" not in html
    assert "javascript:alert" not in html


def test_ai_is_told_which_formatting_works():
    assert "Markdown" in SYSTEM_PROMPT
    assert "images" in SYSTEM_PROMPT


# ---------- Answers that were cut short ----------

def test_cut_off_answer_gets_a_note(auth_client, monkeypatch):
    use_ai(monkeypatch, text="A long answer that stops", is_cut_off=True)
    auth_client.post("/chat/new", data={"message": "Tell me everything"})
    saved = Message.query.filter_by(role="assistant").one().content
    assert saved == "A long answer that stops" + CUT_OFF_NOTE
    html = auth_client.get(f"/chat/{Conversation.query.one().id}").get_data(as_text=True)
    assert "was cut short" in html


def test_complete_answer_has_no_note(auth_client, monkeypatch):
    use_ai(monkeypatch, text="Complete")
    auth_client.post("/chat/new", data={"message": "Hi"})
    assert Message.query.filter_by(role="assistant").one().content == "Complete"


# ---------- Error shown next to the message box ----------

def test_ai_error_appears_by_the_message_box_with_the_text_kept(auth_client, monkeypatch):
    use_ai(monkeypatch, error=AIServiceError("The AI service is busy."))
    html = auth_client.post("/chat/new", data={"message": "Keep this text"}).get_data(as_text=True)
    form = html.split('id="chat-form"')[1]
    assert "The AI service is busy." in form
    assert "still in the box" in form
    assert 'role="alert"' in form
    assert "Keep this text" in form


def test_error_does_not_appear_again_after_reloading(auth_client, monkeypatch):
    use_ai(monkeypatch, error=AIServiceError("The AI service is busy."))
    auth_client.post("/chat/new", data={"message": "Hi"})
    assert "The AI service is busy." not in auth_client.get("/chat/new").get_data(as_text=True)


# ---------- Message limit ----------

def fill_recent_messages(db, count, user=None, minutes_ago=1):
    conversation = Conversation(user=user or get_tester(), title="Busy")
    sent_at = utc_now() - timedelta(minutes=minutes_ago)
    for _ in range(count):
        conversation.messages.append(Message(role="user", content="q", created_at=sent_at))
        conversation.messages.append(Message(role="assistant", content="a", created_at=sent_at))
    db.session.add(conversation)
    db.session.commit()


def test_messages_are_counted_for_this_user_only(db, auth_client, make_user):
    fill_recent_messages(db, 3)
    fill_recent_messages(db, 5, user=make_user("alice"))
    assert count_recent_messages(get_tester().id) == 3


def test_old_messages_do_not_count(db, auth_client):
    fill_recent_messages(db, 3, minutes_ago=MESSAGE_LIMIT_PERIOD.total_seconds() / 60 + 1)
    assert count_recent_messages(get_tester().id) == 0


def test_last_message_under_the_limit_is_allowed(db, auth_client, monkeypatch):
    fill_recent_messages(db, MESSAGE_LIMIT - 1)
    ai = use_ai(monkeypatch)
    assert auth_client.post("/chat/new", data={"message": "Hi"}).status_code == 302
    assert ai.calls == 1


def test_message_over_the_limit_is_refused_without_calling_the_ai(db, auth_client, monkeypatch):
    fill_recent_messages(db, MESSAGE_LIMIT)
    ai = use_ai(monkeypatch)
    response = auth_client.post("/chat/new", data={"message": "One more"})
    assert response.status_code == 200
    assert "which is the limit" in response.get_data(as_text=True)
    assert ai.calls == 0
    assert Message.query.count() == MESSAGE_LIMIT * 2


def test_another_users_limit_does_not_block_this_user(db, auth_client, make_user, monkeypatch):
    fill_recent_messages(db, MESSAGE_LIMIT, user=make_user("alice"))
    use_ai(monkeypatch)
    assert auth_client.post("/chat/new", data={"message": "Hi"}).status_code == 302


def test_limit_also_applies_in_fallback_mode(db, auth_client):
    fill_recent_messages(db, MESSAGE_LIMIT)
    response = auth_client.post("/chat/new", data={"message": "Hi"})
    assert "which is the limit" in response.get_data(as_text=True)
