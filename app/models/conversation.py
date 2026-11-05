"""
Conversation and Message models: the AI chat history.

A conversation is one chat session. It holds many messages, each written
either by the user or by the assistant.
"""

from app.extensions import db
from app.utils import utc_now


class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False, default="New conversation")
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    user = db.relationship("User", back_populates="conversations")
    # order_by keeps messages in the order they were written. The id settles
    # any two messages saved at exactly the same moment.
    messages = db.relationship("Message", back_populates="conversation",
                               cascade="all, delete-orphan",
                               order_by="(Message.created_at, Message.id)")

    def __repr__(self):
        return f"<Conversation {self.id} {self.title!r}>"


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id", ondelete="CASCADE"),
                                nullable=False, index=True)
    role = db.Column(db.String(10), nullable=False)  # "user" or "assistant"
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    conversation = db.relationship("Conversation", back_populates="messages")

    __table_args__ = (
        db.CheckConstraint("role IN ('user', 'assistant')", name="ck_message_role"),
    )

    def __repr__(self):
        return f"<Message {self.id} {self.role}>"
