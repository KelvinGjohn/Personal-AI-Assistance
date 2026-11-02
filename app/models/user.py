"""User model: one row per registered account."""

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager
from app.utils import utc_now


class User(UserMixin, db.Model):
    # UserMixin adds what Flask-Login needs: is_authenticated, get_id(), etc.
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    # Only the hash is stored, never the password itself
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

    def set_password(self, password):
        """Store a salted hash of the password. A hash can't be turned back into the password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Hash the attempt with the same salt and compare it to the stored hash."""
        return check_password_hash(self.password_hash, password)

    @property
    def display_name(self):
        return self.full_name or self.username

    def __repr__(self):
        return f"<User {self.username}>"


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login calls this on each request to turn the id in the session into a User."""
    return db.session.get(User, int(user_id))
