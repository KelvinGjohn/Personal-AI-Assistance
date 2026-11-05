"""
Chat service: sends a user's message to the AI and saves the conversation.

Every lookup includes user_id, so one user can never reach another user's chats.
"""

from app.extensions import db
from app.models import Conversation, Message
from app.services.ai_service import FALLBACK_LABEL, ask_ai
from app.services.common import get_owned_or_404
from app.utils import utc_now

MAX_HISTORY_MESSAGES = 20  # How many earlier messages the AI sees (Day 18 reviews this)
TITLE_LENGTH = 60


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


def build_ai_messages(conversation, text):
    """
    The list of messages to send to the AI: recent history plus the new message.

    Fallback replies are left out, because they aren't real answers and the AI
    shouldn't treat them as things it said.
    """
    history = []
    if conversation is not None:
        history = [message for message in conversation.messages if not is_fallback_message(message)]
        history = history[-MAX_HISTORY_MESSAGES:]

        # A conversation sent to the AI must begin with a user message
        while history and history[0].role != "user":
            history.pop(0)

    messages = [{"role": message.role, "content": message.content} for message in history]
    messages.append({"role": "user", "content": text})
    return messages


def make_title(text):
    """A short title from the first message, on one line."""
    title = " ".join(text.split())
    if len(title) > TITLE_LENGTH:
        return title[:TITLE_LENGTH].rstrip() + "..."
    return title


def send_message(user_id, conversation, text):
    """
    Ask the AI, then save the question and answer together. Returns the
    conversation, which is new if conversation is None.

    Nothing is saved until the AI has answered. If it fails, ask_ai() raises
    AIServiceError and the conversation stays exactly as it was.
    """
    asked_at = utc_now()
    answer = ask_ai(build_ai_messages(conversation, text))

    if conversation is None:
        conversation = Conversation(user_id=user_id, title=make_title(text))
        db.session.add(conversation)

    conversation.messages.append(Message(role="user", content=text, created_at=asked_at))
    conversation.messages.append(Message(role="assistant", content=answer.text))
    # Adding messages doesn't change the conversation's own row, so set this directly
    conversation.updated_at = utc_now()
    db.session.commit()
    return conversation
