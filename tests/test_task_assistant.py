"""
Day 15 - tests for creating a task from plain words (FR-53).

The AI is replaced by FakeAI. The Claude request itself is tested with the
real SDK and a fake network layer, as in test_ai_service.py.
"""

import re
from datetime import datetime

import pytest

from app.models import Task, User
from app.services.ai_service import AIServiceError, ask_ai_json
from app.services.task_assistant import (
    TASK_SCHEMA,
    build_instructions,
    clean_suggestion,
    parse_due_date,
)
from tests.test_ai_service import FakeAPI, api_reply, make_provider

GOOD_ANSWER = {
    "title": "Submit the database report",
    "description": "Chapter 3 needs a diagram",
    "priority": "high",
    "category": "University",
    "due_date": "2099-01-16T17:00",
}


def get_tester():
    return User.query.filter_by(username="tester").first()


class FakeAI:
    """Stands in for ask_ai_json(). Records the call and returns a set answer."""

    def __init__(self, answer=None, error=None):
        self.answer = GOOD_ANSWER if answer is None else answer
        self.error = error
        self.calls = []

    def __call__(self, messages, system, schema):
        self.calls.append({"messages": messages, "system": system, "schema": schema})
        if self.error:
            raise self.error
        return self.answer


@pytest.fixture
def ai_on(app, monkeypatch):
    """A real AI is 'configured', but the call goes to FakeAI."""
    app.config.update(AI_PROVIDER="claude", AI_API_KEY="fake-key-for-tests-only")
    fake = FakeAI()
    monkeypatch.setattr("app.services.task_assistant.ask_ai_json", fake)
    return fake


def ask(client, text="submit the database report by friday, urgent"):
    return client.post("/tasks/assist", data={"request": text})


def field_value(html, name):
    match = re.search(rf'name="{name}"[^>]*value="([^"]*)"', html)
    return match.group(1) if match else None


# ---------- Access ----------

@pytest.mark.parametrize("method", ["get", "post"])
def test_assist_requires_login(client, method):
    response = getattr(client, method)("/tasks/assist")
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login")


def test_task_list_links_to_the_assistant(auth_client):
    assert 'href="/tasks/assist"' in auth_client.get("/tasks").get_data(as_text=True)


# ---------- The suggestion is shown, never saved ----------

def test_suggestion_fills_the_task_form_and_saves_nothing(auth_client, ai_on):
    html = ask(auth_client).get_data(as_text=True)
    assert Task.query.count() == 0
    assert "Check the suggested task" in html
    assert "Suggested by AI" in html
    assert field_value(html, "title") == "Submit the database report"
    assert "Chapter 3 needs a diagram" in html
    assert re.search(r'<option selected value="high">|<option value="high" selected>', html)
    assert field_value(html, "category") == "University"
    assert field_value(html, "due_date") == "2099-01-16T17:00"


def test_confirmation_form_posts_to_the_normal_new_task_page(auth_client, ai_on):
    html = ask(auth_client).get_data(as_text=True)
    assert 'action="/tasks/new"' in html


def test_saving_the_confirmed_form_creates_the_task(auth_client, ai_on):
    html = ask(auth_client).get_data(as_text=True)
    data = {name: field_value(html, name) for name in ("title", "category", "due_date")}
    data.update(description="Chapter 3 needs a diagram", priority="high")
    assert auth_client.post("/tasks/new", data=data).status_code == 302

    task = Task.query.one()
    assert task.user_id == get_tester().id
    assert task.title == "Submit the database report"
    assert task.due_date == datetime(2099, 1, 16, 17, 0)


def test_user_can_change_the_suggestion_before_saving(auth_client, ai_on):
    ask(auth_client)
    auth_client.post("/tasks/new", data={"title": "My own title", "priority": "low",
                                         "description": "", "category": "", "due_date": ""})
    task = Task.query.one()
    assert task.title == "My own title"
    assert task.priority == "low"
    assert task.due_date is None


def test_date_in_the_suggestion_is_the_users_local_time(db, auth_client, ai_on):
    """The AI answers in the user's time, and saving converts it to UTC as usual."""
    get_tester().timezone = "Asia/Tokyo"
    db.session.commit()
    html = ask(auth_client).get_data(as_text=True)
    assert field_value(html, "due_date") == "2099-01-16T17:00"
    auth_client.post("/tasks/new", data={"title": "T", "priority": "high", "description": "",
                                         "category": "", "due_date": "2099-01-16T17:00"})
    assert Task.query.one().due_date == datetime(2099, 1, 16, 8, 0)


# ---------- What the AI is told ----------

def test_ai_gets_the_request_the_schema_and_todays_date(db, auth_client, ai_on):
    get_tester().timezone = "Asia/Tokyo"
    db.session.commit()
    ask(auth_client, "pay the phone bill tomorrow")
    call = ai_on.calls[0]
    assert call["messages"] == [{"role": "user", "content": "pay the phone bill tomorrow"}]
    assert call["schema"] == TASK_SCHEMA
    assert "Asia/Tokyo" in call["system"]
    assert "YYYY-MM-DDTHH:MM" in call["system"]


def test_ai_is_told_the_users_categories_but_not_other_users(db, auth_client, make_user, ai_on):
    alice = make_user("alice")
    db.session.add_all([Task(user=get_tester(), title="a", category="Home"),
                        Task(user=alice, title="b", category="AliceSecret")])
    db.session.commit()
    ask(auth_client)
    assert "Home" in ai_on.calls[0]["system"]
    assert "AliceSecret" not in ai_on.calls[0]["system"]


def test_instructions_include_the_weekday():
    text = build_instructions(datetime(2026, 11, 8, 14, 30), "UTC", [])
    assert "Sunday 08 November 2026, 14:30" in text
    assert "none yet" in text


def test_schema_only_allows_known_fields_and_priorities():
    assert TASK_SCHEMA["additionalProperties"] is False
    assert TASK_SCHEMA["properties"]["priority"]["enum"] == ["low", "medium", "high"]
    assert set(TASK_SCHEMA["required"]) == set(TASK_SCHEMA["properties"])


# ---------- Checking the AI's answer ----------

@pytest.mark.parametrize("text, expected", [
    ("2099-01-16T17:00", datetime(2099, 1, 16, 17, 0)),
    ("", None),
    (None, None),
    ("next friday", None),
    ("2099-02-30T10:00", None),
    ("1999-12-31T10:00", None),
    ("9999-01-01T10:00", None),
])
def test_parse_due_date(text, expected):
    assert parse_due_date(text) == expected


def test_bad_values_from_the_ai_become_safe_defaults():
    data = {"title": "x" * 500, "priority": "urgent!!", "category": "c" * 80,
            "description": "d" * 6000, "due_date": "soon"}
    values = clean_suggestion(data, "request")
    assert len(values["title"]) == 200
    assert values["priority"] == "medium"
    assert len(values["category"]) == 50
    assert len(values["description"]) == 5000
    assert values["due_date"] is None


def test_empty_title_from_the_ai_falls_back_to_the_request():
    assert clean_suggestion({"title": "   "}, "buy milk")["title"] == "buy milk"


def test_missing_fields_do_not_crash():
    values = clean_suggestion({}, "buy milk")
    assert values == {"title": "buy milk", "description": "", "priority": "medium",
                      "category": "", "due_date": None}


def test_html_from_the_ai_is_shown_as_text(auth_client, app, monkeypatch):
    app.config.update(AI_PROVIDER="claude", AI_API_KEY="fake-key-for-tests-only")
    bad = "<script>alert(1)</script>"
    fake = FakeAI(answer={**GOOD_ANSWER, "title": bad, "description": bad, "category": bad})
    monkeypatch.setattr("app.services.task_assistant.ask_ai_json", fake)
    assert bad not in ask(auth_client).get_data(as_text=True)


# ---------- Without an AI provider ----------

def test_fallback_uses_the_request_as_title_and_says_it_is_not_ai(auth_client, monkeypatch):
    fake = FakeAI()
    monkeypatch.setattr("app.services.task_assistant.ask_ai_json", fake)
    html = ask(auth_client, "buy milk on saturday").get_data(as_text=True)
    assert fake.calls == []
    assert "Development mode - not AI" in html
    assert "Suggested by AI" not in html
    assert field_value(html, "title") == "buy milk on saturday"
    assert field_value(html, "due_date") in (None, "")
    assert Task.query.count() == 0


def test_ask_ai_json_refuses_to_run_in_fallback_mode(app):
    with pytest.raises(AIServiceError, match="needs an AI provider"):
        ask_ai_json([{"role": "user", "content": "x"}], "system", TASK_SCHEMA)


# ---------- Errors ----------

@pytest.mark.parametrize("text, message", [
    ("", "Describe the task first."),
    ("   ", "Describe the task first."),
    ("x" * 1001, "1000 characters or fewer"),
])
def test_invalid_request_is_refused_without_calling_the_ai(auth_client, ai_on, text, message):
    response = ask(auth_client, text)
    assert message in response.get_data(as_text=True)
    assert ai_on.calls == []


def test_ai_failure_is_shown_and_the_text_kept(auth_client, app, monkeypatch):
    app.config.update(AI_PROVIDER="claude", AI_API_KEY="fake-key-for-tests-only")
    monkeypatch.setattr("app.services.task_assistant.ask_ai_json",
                        FakeAI(error=AIServiceError("The AI service is busy.")))
    html = ask(auth_client, "keep this request").get_data(as_text=True)
    assert "The AI service is busy." in html
    assert "keep this request" in html
    assert Task.query.count() == 0


def test_assist_needs_a_csrf_token(app, auth_client, ai_on):
    app.config["WTF_CSRF_ENABLED"] = True
    assert ask(auth_client).status_code == 400
    assert ai_on.calls == []


def test_confirmation_form_has_a_working_csrf_token(app, auth_client, ai_on):
    app.config["WTF_CSRF_ENABLED"] = True
    html = auth_client.get("/tasks/assist").get_data(as_text=True)
    token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)
    html = auth_client.post("/tasks/assist", data={"request": "x", "csrf_token": token}).get_data(as_text=True)
    token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)
    data = {"csrf_token": token, "title": "T", "priority": "high", "description": "",
            "category": "", "due_date": ""}
    assert auth_client.post("/tasks/new", data=data).status_code == 302


# ---------- The Claude request (real SDK, fake network) ----------

def test_claude_is_asked_for_json_in_the_schema(app):
    fake_api = FakeAPI(body=api_reply([{"type": "text", "text": '{"title": "T"}'}]))
    result = make_provider(fake_api).ask_json([{"role": "user", "content": "x"}], "system", TASK_SCHEMA)
    assert result == {"title": "T"}
    output_config = fake_api.last_body["output_config"]
    assert output_config["format"] == {"type": "json_schema", "schema": TASK_SCHEMA}
    assert output_config["effort"] == "low"


@pytest.mark.parametrize("text, stop_reason, message", [
    ("not json", "end_turn", "couldn't be read"),
    ('{"title": "cut', "max_tokens", "too long"),
    ('{"title": "T"}', "refusal", "can't help"),
])
def test_bad_claude_json_answers_become_friendly_errors(app, text, stop_reason, message):
    body = api_reply([{"type": "text", "text": text}], stop_reason=stop_reason)
    with pytest.raises(AIServiceError, match=message):
        make_provider(FakeAPI(body=body)).ask_json([{"role": "user", "content": "x"}], "s", TASK_SCHEMA)


def test_normal_chat_answers_still_use_medium_effort(app):
    fake_api = FakeAPI()
    make_provider(fake_api).ask([{"role": "user", "content": "x"}], "system")
    assert fake_api.last_body["output_config"] == {"effort": "medium"}
