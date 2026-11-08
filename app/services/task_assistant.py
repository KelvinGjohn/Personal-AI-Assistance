"""
Task assistant: turns a plain-language request into a suggested task (FR-53).

It only makes a suggestion. The suggestion fills in the normal task form, the
user checks or changes it, and nothing is saved until they press Save.
"""

from dataclasses import dataclass
from datetime import datetime

from app.forms.task_forms import MAX_YEAR, MIN_YEAR
from app.models.task import PRIORITIES
from app.services.ai_service import ask_ai_json, is_fallback_mode
from app.utils import to_user_time, utc_now

DATE_FORMAT = "%Y-%m-%dT%H:%M"
TITLE_LENGTH = 200
CATEGORY_LENGTH = 50
DESCRIPTION_LENGTH = 5000

# The shape the AI's answer must have. An empty string means "not given".
TASK_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "priority": {"type": "string", "enum": list(PRIORITIES)},
        "category": {"type": "string"},
        "due_date": {"type": "string"},
    },
    "required": ["title", "description", "priority", "category", "due_date"],
    "additionalProperties": False,
}


@dataclass
class TaskSuggestion:
    values: dict           # ready to fill in the TaskForm
    made_by_ai: bool


def build_instructions(local_now, timezone_name, categories):
    """The instructions for the AI. Today's date lets it work out words like "Friday"."""
    existing = ", ".join(categories) if categories else "none yet"
    return (
        "Turn the user's request into one to-do task for a task manager.\n"
        f"Now it is {local_now.strftime('%A %d %B %Y, %H:%M')} in the user's time zone ({timezone_name}).\n"
        "title: a short action, at most 100 characters, such as 'Submit the database report'.\n"
        "description: extra details from the request, or an empty string if there are none.\n"
        "priority: 'high' if the request says it is urgent or important, 'low' if it says it "
        "can wait, otherwise 'medium'.\n"
        f"category: one of the user's categories if one clearly fits ({existing}), a short new "
        "category if the request names one, otherwise an empty string.\n"
        "due_date: the deadline in the user's time zone, written as YYYY-MM-DDTHH:MM, or an "
        "empty string if the request has no deadline. If only a day is given, use 17:00. "
        "Words like 'Friday' mean the next one from today."
    )


def parse_due_date(text):
    """The AI's date, or None if it is empty, badly written or out of range."""
    try:
        value = datetime.strptime(text.strip(), DATE_FORMAT)
    except (ValueError, AttributeError):
        return None
    return value if MIN_YEAR <= value.year <= MAX_YEAR else None


def short(text, limit):
    return " ".join(str(text or "").split())[:limit].strip()


def clean_suggestion(data, request_text):
    """
    Check every value from the AI, because it is still outside input.
    Anything wrong is replaced with a safe default instead of causing an error.
    """
    title = short(data.get("title"), TITLE_LENGTH) or short(request_text, TITLE_LENGTH)
    priority = data.get("priority")
    return {
        "title": title,
        "description": str(data.get("description") or "").strip()[:DESCRIPTION_LENGTH],
        "priority": priority if priority in PRIORITIES else "medium",
        "category": short(data.get("category"), CATEGORY_LENGTH),
        "due_date": parse_due_date(data.get("due_date")),
    }


def suggest_task(request_text, timezone_name, categories):
    """
    A TaskSuggestion for the request. Raises AIServiceError if the AI fails.

    Without an AI provider, the request simply becomes the title, and
    made_by_ai is False so the page can say nothing was worked out.
    """
    if is_fallback_mode():
        return TaskSuggestion(values=clean_suggestion({}, request_text), made_by_ai=False)

    instructions = build_instructions(to_user_time(utc_now()), timezone_name, categories)
    data = ask_ai_json([{"role": "user", "content": request_text}], instructions, TASK_SCHEMA)
    return TaskSuggestion(values=clean_suggestion(data, request_text), made_by_ai=True)
