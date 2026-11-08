"""
Reminder assistant: turns a plain-language request into a suggested reminder (FR-54).

Like the task assistant, it only fills in the normal form. In addition it
works out what the request didn't say. A reminder needs a date and a time,
and the app asks for anything missing instead of guessing it.
"""

from dataclasses import dataclass, field
from datetime import date, datetime

from app.forms.task_forms import MAX_YEAR, MIN_YEAR
from app.services.ai_service import ask_ai_json, is_fallback_mode
from app.services.task_assistant import short
from app.utils import to_user_time, utc_now

TITLE_LENGTH = 200
DESCRIPTION_LENGTH = 5000

# The shape the AI's answer must have. An empty string means "not given".
REMINDER_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "date": {"type": "string"},
        "time": {"type": "string"},
    },
    "required": ["title", "description", "date", "time"],
    "additionalProperties": False,
}


@dataclass
class ReminderSuggestion:
    values: dict                 # ready to fill in the ReminderForm
    made_by_ai: bool
    missing: list = field(default_factory=list)   # e.g. ["a time"], shown as a question
    known_date: date = None      # a date the request gave, even if the time is missing
    passed_time: datetime = None  # a time the request gave that has already passed


def build_instructions(local_now, timezone_name):
    """The instructions for the AI. Today's date lets it work out words like "Friday"."""
    return (
        "Turn the user's request into one reminder for a reminder app.\n"
        f"Now it is {local_now.strftime('%A %d %B %Y, %H:%M')} in the user's time zone ({timezone_name}).\n"
        "title: what to be reminded about, short, such as 'Call the dentist'.\n"
        "description: extra details from the request, or an empty string if there are none.\n"
        "date: the day in the user's time zone as YYYY-MM-DD, or an empty string if the request "
        "doesn't say which day. 'Today', 'tomorrow' and weekday names count as a day; "
        "a weekday means the next one from today.\n"
        "time: the time of day as HH:MM (24-hour), or an empty string if the request doesn't say. "
        "You may use 09:00 for 'morning', 14:00 for 'afternoon', 18:00 for 'evening' and 20:00 "
        "for 'tonight'. Never make up a time the request doesn't give."
    )


def parse_date(text):
    try:
        value = datetime.strptime(str(text or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None
    return value if MIN_YEAR <= value.year <= MAX_YEAR else None


def parse_time(text):
    try:
        return datetime.strptime(str(text or "").strip(), "%H:%M").time()
    except ValueError:
        return None


def clean_suggestion(data, request_text, local_now):
    """
    Check every value from the AI and work out what is missing.
    local_now is the current time in the user's time zone, without tzinfo.
    """
    title = short(data.get("title"), TITLE_LENGTH) or short(request_text, TITLE_LENGTH)
    description = str(data.get("description") or "").strip()[:DESCRIPTION_LENGTH]
    day = parse_date(data.get("date"))
    clock = parse_time(data.get("time"))

    suggestion = ReminderSuggestion(
        values={"title": title, "description": description, "remind_at": None},
        made_by_ai=True,
        known_date=day,
    )

    if day is None:
        suggestion.missing.append("a date")
    if clock is None:
        suggestion.missing.append("a time")
    if day is None or clock is None:
        return suggestion

    remind_at = datetime.combine(day, clock)
    if remind_at <= local_now:
        # Leave the field empty, so it can't be saved without choosing a new time
        suggestion.passed_time = remind_at
    else:
        suggestion.values["remind_at"] = remind_at
    return suggestion


def suggest_reminder(request_text, timezone_name):
    """
    A ReminderSuggestion for the request. Raises AIServiceError if the AI fails.

    Without an AI provider, the request becomes the title and the date and
    time are asked for, with made_by_ai False so the page can say so.
    """
    local_now = to_user_time(utc_now()).replace(tzinfo=None)

    if is_fallback_mode():
        suggestion = clean_suggestion({}, request_text, local_now)
        suggestion.made_by_ai = False
        return suggestion

    instructions = build_instructions(local_now, timezone_name)
    data = ask_ai_json([{"role": "user", "content": request_text}], instructions, REMINDER_SCHEMA)
    return clean_suggestion(data, request_text, local_now)
