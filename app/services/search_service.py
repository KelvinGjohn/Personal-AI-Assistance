"""
Global search: one search across the user's tasks, reminders, notes and chats.

Every query starts from the logged-in user's id, so results can never include
another user's records. Matching follows app/text_search.py: every word must
appear somewhere in the record, ignoring upper and lower case and accents.
"""

from dataclasses import dataclass, field

from flask import url_for

from app.models import Conversation, Message, Note, Reminder, Task
from app.text_search import all_words_match, contains, find_snippet, search_words

TYPES = ("tasks", "reminders", "notes", "chats")
TYPE_LABELS = {"tasks": "Tasks", "reminders": "Reminders", "notes": "Notes", "chats": "Chats"}
PREVIEW_COUNT = 5     # results per type when searching everything
SINGLE_TYPE_COUNT = 50  # results when one type is chosen


@dataclass
class SearchResult:
    title: str
    url: str
    detail: str = ""        # a short line under the title, such as a date or category
    snippet: tuple = None   # (before, match, after) around the first matching word


@dataclass
class ResultGroup:
    type: str
    label: str
    total: int
    results: list = field(default_factory=list)


def task_query(user_id, q):
    columns = [Task.title, Task.description, Task.category]
    return (Task.query.filter_by(user_id=user_id).filter(all_words_match(columns, q))
            .order_by(Task.is_completed, Task.due_date.is_(None), Task.due_date, Task.id.desc()))


def reminder_query(user_id, q):
    columns = [Reminder.title, Reminder.description]
    return (Reminder.query.filter_by(user_id=user_id).filter(all_words_match(columns, q))
            .order_by(Reminder.remind_at.desc(), Reminder.id.desc()))


def note_query(user_id, q):
    columns = [Note.title, Note.content, Note.category]
    return (Note.query.filter_by(user_id=user_id).filter(all_words_match(columns, q))
            .order_by(Note.updated_at.desc(), Note.id.desc()))


def chat_query(user_id, q):
    """
    A chat matches if every word appears in its title or in any of its
    messages. Message.conversation.has() / Conversation.messages.any() become
    EXISTS sub-queries, so each chat appears once however many messages match.
    """
    query = Conversation.query.filter_by(user_id=user_id)
    for word in search_words(q):
        query = query.filter(
            contains(Conversation.title, word)
            | Conversation.messages.any(contains(Message.content, word))
        )
    return query.order_by(Conversation.updated_at.desc(), Conversation.id.desc())


def to_result(kind, record, q, format_time):
    """Turn a record into a SearchResult for the page."""
    if kind == "tasks":
        status = "Finished" if record.is_completed else record.priority.capitalize() + " priority"
        due = f" · Due {format_time(record.due_date)}" if record.due_date else ""
        return SearchResult(record.title, url_for("tasks.edit", task_id=record.id), status + due,
                            find_snippet(record.description, q))
    if kind == "reminders":
        return SearchResult(record.title, url_for("reminders.edit", reminder_id=record.id),
                            f"{record.status.capitalize()} · {format_time(record.remind_at)}",
                            find_snippet(record.description, q))
    if kind == "notes":
        return SearchResult(record.title, url_for("notes.view", note_id=record.id),
                            record.category or "", find_snippet(record.content, q))
    # chats: show where a message matched, if the title alone didn't
    snippet = None
    for message in record.messages:
        snippet = find_snippet(message.content, q)
        if snippet:
            break
    return SearchResult(record.title, url_for("chat.conversation", conversation_id=record.id),
                        f"Last used {format_time(record.updated_at)}", snippet)


QUERIES = {"tasks": task_query, "reminders": reminder_query, "notes": note_query, "chats": chat_query}


def search(user_id, q, only_type, format_time):
    """
    The search results as a list of ResultGroup, one per type searched.
    format_time turns a stored UTC time into text in the user's time zone.
    """
    if not search_words(q):
        return []
    types = [only_type] if only_type in TYPES else list(TYPES)
    limit = SINGLE_TYPE_COUNT if only_type in TYPES else PREVIEW_COUNT

    groups = []
    for kind in types:
        query = QUERIES[kind](user_id, q)
        records = query.limit(limit).all()
        groups.append(ResultGroup(
            type=kind,
            label=TYPE_LABELS[kind],
            total=query.count(),
            results=[to_result(kind, record, q, format_time) for record in records],
        ))
    return groups
