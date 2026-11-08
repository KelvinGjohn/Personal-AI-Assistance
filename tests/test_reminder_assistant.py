"""
Day 16 - tests for creating a reminder from plain words (FR-54).

The AI is replaced by FakeAI, so nothing leaves this computer.
"""

import re
from datetime import date, datetime, timedelta

import pytest

from app.models import Reminder, User
from app.services.ai_service import AIServiceError
from app.services.reminder_assistant import (
    REMINDER_SCHEMA,
    build_instructions,
    clean_suggestion,
    parse_date,
    parse_time,
)
from app.utils import to_user_time, utc_now

NOW = datetime(2026, 11, 8, 10, 0)  # local time used by the clean_suggestion tests

FULL_ANSWER = {
    "title": "Call the dentist",
    "description": "Ask about the filling",
    "date": "2099-01-16",
    "time": "10:30",
}


def get_tester():
    return User.query.filter_by(username="tester").first()


class FakeAI:
    def __init__(self, answer=None, error=None):
        self.answer = FULL_ANSWER if answer is None else answer
        self.error = error
        self.calls = []

    def __call__(self, messages, system, schema):
        self.calls.append({"messages": messages, "system": system, "schema": schema})
        if self.error:
            raise self.error
        return self.answer


@pytest.fixture
def use_ai(app, monkeypatch):
    """Returns a function that makes the 'configured' AI give a chosen answer."""
    app.config.update(AI_PROVIDER="claude", AI_API_KEY="fake-key-for-tests-only")

    def _use_ai(answer=None, error=None):
        fake = FakeAI(answer, error)
        monkeypatch.setattr("app.services.reminder_assistant.ask_ai_json", fake)
        return fake

    return _use_ai


def ask(client, text="remind me to call the dentist on friday at 10:30"):
    return client.post("/reminders/assist", data={"request": text})


def remind_at_value(html):
    match = re.search(r'name="remind_at"[^>]*value="([^"]*)"', html)
    return match.group(1) if match else ""


# ---------- Access and links ----------

@pytest.mark.parametrize("method", ["get", "post"])
def test_assist_requires_login(client, method):
    response = getattr(client, method)("/reminders/assist")
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login")


def test_reminder_list_links_to_the_assistant(auth_client):
    assert 'href="/reminders/assist"' in auth_client.get("/reminders").get_data(as_text=True)


def test_request_page_is_worded_for_reminders(auth_client):
    html = auth_client.get("/reminders/assist").get_data(as_text=True)
    assert "Create a reminder with AI" in html
    assert "Describe the reminder" in html
    assert 'href="/reminders/new"' in html


def test_task_request_page_still_worded_for_tasks(auth_client):
    html = auth_client.get("/tasks/assist").get_data(as_text=True)
    assert "Create a task with AI" in html
    assert 'href="/tasks/new"' in html


# ---------- A complete request ----------

def test_complete_request_fills_the_form_and_saves_nothing(auth_client, use_ai):
    use_ai()
    html = ask(auth_client).get_data(as_text=True)
    assert Reminder.query.count() == 0
    assert "Check the suggested reminder" in html
    assert "Suggested by AI" in html
    assert 'value="Call the dentist"' in html
    assert "Ask about the filling" in html
    assert remind_at_value(html) == "2099-01-16T10:30"
    assert 'action="/reminders/new"' in html
    assert "When should I remind you" not in html
    assert "What time?" not in html


def test_confirmed_form_saves_the_reminder_in_utc(db, auth_client, use_ai):
    get_tester().timezone = "Asia/Tokyo"
    db.session.commit()
    use_ai()
    ask(auth_client)
    data = {"title": "Call the dentist", "description": "", "remind_at": "2099-01-16T10:30"}
    assert auth_client.post("/reminders/new", data=data).status_code == 302
    reminder = Reminder.query.one()
    assert reminder.user_id == get_tester().id
    assert reminder.remind_at == datetime(2099, 1, 16, 1, 30)


# ---------- Asking for missing details (FR-54) ----------

def test_missing_time_asks_what_time_and_shows_the_date(auth_client, use_ai):
    use_ai({**FULL_ANSWER, "time": ""})
    html = ask(auth_client, "remind me to call the dentist on friday").get_data(as_text=True)
    assert "What time?" in html
    assert "Friday 16 January 2099" in html
    assert remind_at_value(html) == ""
    assert Reminder.query.count() == 0


def test_missing_date_asks_when(auth_client, use_ai):
    use_ai({**FULL_ANSWER, "date": ""})
    html = ask(auth_client, "remind me to stretch at 10:30").get_data(as_text=True)
    assert "When should I remind you?" in html
    assert "didn't say a date" in html
    assert remind_at_value(html) == ""


def test_missing_date_and_time_asks_for_both(auth_client, use_ai):
    use_ai({**FULL_ANSWER, "date": "", "time": ""})
    html = ask(auth_client, "remind me to call the dentist").get_data(as_text=True)
    assert "a date or a time" in html


def test_form_cannot_be_saved_until_the_time_is_given(auth_client, use_ai):
    use_ai({**FULL_ANSWER, "time": ""})
    ask(auth_client)
    response = auth_client.post("/reminders/new", data={"title": "Call the dentist", "remind_at": ""})
    assert "Enter a valid date and time." in response.get_data(as_text=True)
    assert Reminder.query.count() == 0


def test_time_that_already_passed_is_not_filled_in(auth_client, use_ai):
    earlier = to_user_time(utc_now() - timedelta(days=2))
    use_ai({**FULL_ANSWER, "date": earlier.strftime("%Y-%m-%d"), "time": earlier.strftime("%H:%M")})
    html = ask(auth_client, "remind me at that time").get_data(as_text=True)
    assert "That time has already passed" in html
    assert remind_at_value(html) == ""


# ---------- Checking the AI's answer ----------

@pytest.mark.parametrize("text, expected", [
    ("2099-01-16", date(2099, 1, 16)),
    ("", None),
    (None, None),
    ("friday", None),
    ("2099-02-30", None),
    ("1999-12-31", None),
])
def test_parse_date(text, expected):
    assert parse_date(text) == expected


@pytest.mark.parametrize("text, ok", [
    ("10:30", True), ("00:00", True), ("23:59", True),
    ("", False), (None, False), ("25:00", False), ("10am", False), ("morning", False),
])
def test_parse_time(text, ok):
    assert (parse_time(text) is not None) is ok


def test_clean_suggestion_complete():
    suggestion = clean_suggestion(FULL_ANSWER, "request", NOW)
    assert suggestion.values["remind_at"] == datetime(2099, 1, 16, 10, 30)
    assert suggestion.missing == []
    assert suggestion.passed_time is None


@pytest.mark.parametrize("answer, missing", [
    ({**FULL_ANSWER, "time": ""}, ["a time"]),
    ({**FULL_ANSWER, "date": ""}, ["a date"]),
    ({**FULL_ANSWER, "date": "", "time": ""}, ["a date", "a time"]),
    ({**FULL_ANSWER, "date": "nonsense", "time": "25:99"}, ["a date", "a time"]),
    ({}, ["a date", "a time"]),
])
def test_clean_suggestion_finds_what_is_missing(answer, missing):
    suggestion = clean_suggestion(answer, "request", NOW)
    assert suggestion.missing == missing
    assert suggestion.values["remind_at"] is None


def test_clean_suggestion_keeps_a_known_date_when_the_time_is_missing():
    suggestion = clean_suggestion({**FULL_ANSWER, "time": ""}, "request", NOW)
    assert suggestion.known_date == date(2099, 1, 16)


@pytest.mark.parametrize("when, passed", [
    (NOW - timedelta(minutes=1), True),
    (NOW, True),
    (NOW + timedelta(minutes=1), False),
])
def test_clean_suggestion_spots_a_time_that_has_passed(when, passed):
    answer = {**FULL_ANSWER, "date": when.strftime("%Y-%m-%d"), "time": when.strftime("%H:%M")}
    suggestion = clean_suggestion(answer, "request", NOW)
    assert (suggestion.passed_time is not None) is passed
    assert (suggestion.values["remind_at"] is None) is passed


def test_bad_and_long_text_from_the_ai_is_made_safe():
    suggestion = clean_suggestion({"title": "x" * 500, "description": "d" * 6000}, "req", NOW)
    assert len(suggestion.values["title"]) == 200
    assert len(suggestion.values["description"]) == 5000


def test_empty_title_from_the_ai_falls_back_to_the_request():
    assert clean_suggestion({"title": " "}, "call mum", NOW).values["title"] == "call mum"


def test_html_from_the_ai_is_shown_as_text(auth_client, use_ai):
    bad = "<script>alert(1)</script>"
    use_ai({**FULL_ANSWER, "title": bad, "description": bad})
    assert bad not in ask(auth_client).get_data(as_text=True)


# ---------- What the AI is told ----------

def test_ai_gets_the_request_schema_and_local_date(db, auth_client, use_ai):
    get_tester().timezone = "Europe/Paris"
    db.session.commit()
    fake = use_ai()
    ask(auth_client, "remind me to pay rent tomorrow at 9")
    call = fake.calls[0]
    assert call["messages"] == [{"role": "user", "content": "remind me to pay rent tomorrow at 9"}]
    assert call["schema"] == REMINDER_SCHEMA
    assert "Europe/Paris" in call["system"]


def test_instructions_forbid_made_up_times_and_include_the_weekday():
    text = build_instructions(datetime(2026, 11, 8, 14, 30), "UTC")
    assert "Sunday 08 November 2026, 14:30" in text
    assert "Never make up a time" in text


def test_schema_has_only_the_four_fields():
    assert set(REMINDER_SCHEMA["properties"]) == {"title", "description", "date", "time"}
    assert REMINDER_SCHEMA["additionalProperties"] is False


# ---------- Fallback and errors ----------

def test_fallback_asks_for_date_and_time_and_says_it_is_not_ai(auth_client, monkeypatch):
    fake = FakeAI()
    monkeypatch.setattr("app.services.reminder_assistant.ask_ai_json", fake)
    html = ask(auth_client, "call mum on sunday").get_data(as_text=True)
    assert fake.calls == []
    assert "Development mode - not AI" in html
    assert "Suggested by AI" not in html
    assert 'value="call mum on sunday"' in html
    assert "a date or a time" in html
    assert Reminder.query.count() == 0


@pytest.mark.parametrize("text, message", [
    ("", "Describe the reminder first."),
    ("x" * 1001, "1000 characters or fewer"),
])
def test_invalid_request_is_refused_without_calling_the_ai(auth_client, use_ai, text, message):
    fake = use_ai()
    assert message in ask(auth_client, text).get_data(as_text=True)
    assert fake.calls == []


def test_ai_failure_is_shown_and_the_text_kept(auth_client, use_ai):
    use_ai(error=AIServiceError("The AI service is busy."))
    html = ask(auth_client, "keep this request").get_data(as_text=True)
    assert "The AI service is busy." in html
    assert "keep this request" in html
    assert Reminder.query.count() == 0


def test_assist_needs_a_csrf_token(app, auth_client, use_ai):
    fake = use_ai()
    app.config["WTF_CSRF_ENABLED"] = True
    assert ask(auth_client).status_code == 400
    assert fake.calls == []
