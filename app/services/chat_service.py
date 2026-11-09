"""
Chat service: sends a user's message to the AI and saves the conversation.

Every lookup includes user_id, so one user can never reach another user's chats.
"""

from datetime import timedelta

from sqlalchemy import func

from app.extensions import db
from app.models import Conversation, Message
from app.services.ai_service import FALLBACK_LABEL, AIServiceError, ask_ai
from app.services.common import get_owned_or_404
from app.services.personal_data import add_context_to_question
from app.utils import utc_now

# How much of a chat the AI "remembers": the last 20 messages, but never more
# than about 40,000 characters (roughly 10,000 tokens), so a chat with very
# long answers doesn't become slow and expensive. The oldest messages go first.
MAX_HISTORY_MESSAGES = 20
MAX_HISTORY_CHARACTERS = 40_000
TITLE_LENGTH = 60

# Each AI answer costs money, so one account can't send an unlimited number
MESSAGE_LIMIT = 50
MESSAGE_LIMIT_PERIOD = timedelta(hours=1)

CUT_OFF_NOTE = "\n\n*(This answer reached the length limit and was cut short.)*"


def count_recent_messages(user_id, now=None):
    """How many messages this user sent in the last MESSAGE_LIMIT_PERIOD, across all chats."""
    if now is None:
        now = utc_now()
    return (
        Message.query.join(Conversation)
        .filter(
            Conversation.user_id == user_id,
            Message.role == "user",
            Message.created_at >= now - MESSAGE_LIMIT_PERIOD,
        )
        .count()
    )


def get_user_conversation_or_404(user_id, conversation_id):
    return get_owned_or_404(Conversation, user_id, conversation_id)


def get_latest_conversation(user_id):
    """The chat the user used most recently, or None if they have no chats yet."""
    return (
        Conversation.query.filter_by(user_id=user_id)
        .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        .first()
    )


def is_fallback_message(message):
    """True if this saved message came from the fallback, not from an AI."""
    return message.role == "assistant" and message.content.startswith(FALLBACK_LABEL)


def build_ai_messages(conversation, text, personal_context=None):
    """
    The list of messages to send to the AI: recent history plus the new message.

    Fallback replies are left out, because they aren't real answers and the AI
    shouldn't treat them as things it said.

    personal_context (the user's own data) is added to the new message only.
    It is never saved, so later messages don't send it again unless asked.
    """
    history = []
    if conversation is not None:
        history = [message for message in conversation.messages if not is_fallback_message(message)]
        history = history[-MAX_HISTORY_MESSAGES:]
        while history and sum(len(message.content) for message in history) > MAX_HISTORY_CHARACTERS:
            history.pop(0)

        # A conversation sent to the AI must begin with a user message
        while history and history[0].role != "user":
            history.pop(0)

    messages = [{"role": message.role, "content": message.content} for message in history]
    if personal_context:
        text = add_context_to_question(personal_context, text)
    messages.append({"role": "user", "content": text})
    return messages


def make_title(text):
    """A short title from the first message, on one line."""
    title = " ".join(text.split())
    if len(title) > TITLE_LENGTH:
        return title[:TITLE_LENGTH].rstrip() + "..."
    return title


def send_message(user_id, conversation, text, personal_context=None):
    """
    Ask the AI, then save the question and answer together. Returns the
    conversation, which is new if conversation is None.

    Nothing is saved until the AI has answered. If it fails, ask_ai() raises
    AIServiceError and the conversation stays exactly as it was.
    """
    asked_at = utc_now()
    if count_recent_messages(user_id, asked_at) >= MESSAGE_LIMIT:
        raise AIServiceError(
            f"You've sent {MESSAGE_LIMIT} messages in the last hour, which is the limit. "
            "Please wait a while and try again."
        )

    answer = ask_ai(build_ai_messages(conversation, text, personal_context))
    answer_text = answer.text + CUT_OFF_NOTE if answer.is_cut_off else answer.text

    if conversation is None:
        conversation = Conversation(user_id=user_id, title=make_title(text))
        db.session.add(conversation)

    conversation.messages.append(Message(role="user", content=text, created_at=asked_at))
    conversation.messages.append(Message(role="assistant", content=answer_text))
    # Adding messages doesn't change the conversation's own row, so set this directly
    conversation.updated_at = utc_now()
    db.session.commit()
    return conversation


def build_conversation_list(user_id):
    """
    The user's chats, most recently used first, each with its number of messages.

    Counting in the database with GROUP BY means the messages themselves
    aren't loaded just to count them. Each item is (conversation, count).
    """
    return (
        db.session.query(Conversation, func.count(Message.id))
        .outerjoin(Message)
        .filter(Conversation.user_id == user_id)
        .group_by(Conversation.id)
        .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
    )
