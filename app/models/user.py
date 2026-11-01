"""User model: one row per registered account."""

from app.extensions import db
from app.utils import utc_now


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    # Only the hash is stored, never the password itself (hashing is added on Day 7)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100))
    timezone = db.Column(db.String(50), nullable=False, default="UTC")
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    # One user has many tasks, reminders, notes, conversations and notifications.
    # cascade="all, delete-orphan": deleting a user also deletes all their data.
    tasks = db.relationship("Task", back_populates="user", cascade="all, delete-orphan")
    reminders = db.relationship("Reminder", back_populates="user", cascade="all, delete-orphan")
    notes = db.relationship("Note", back_populates="user", cascade="all, delete-orphan")
    conversations = db.relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    notifications = db.relationship("Notification", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username}>"
