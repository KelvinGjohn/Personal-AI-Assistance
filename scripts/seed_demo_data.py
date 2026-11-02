"""
Fill the development database with a demo user and sample data, so the
dashboard has something to show.

    python scripts/seed_demo_data.py

Running it again replaces the demo user's data. Other users are not touched.
All dates are relative to now, so "upcoming" items are always upcoming.
"""

import sys
from datetime import timedelta
from pathlib import Path

# Lets this script import the "app" package from the project folder
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Conversation, Message, Note, Reminder, Task, User  # noqa: E402
from app.utils import utc_now  # noqa: E402

DEMO_USERNAME = "demo"


def seed_demo_data():
    """Delete the old demo user (and, by cascade, their data), then create a new one."""
    old_user = User.query.filter_by(username=DEMO_USERNAME).first()
    if old_user:
        db.session.delete(old_user)
        db.session.commit()

    now = utc_now()
    # "!" is not a valid password hash, so nobody can ever log in as this user
    user = User(username=DEMO_USERNAME, email="demo@example.com",
                password_hash="!", full_name="Demo User")

    user.tasks = [
        Task(title="Submit database assignment", priority="high", category="University",
             due_date=now - timedelta(days=1)),
        Task(title="Revise for algorithms exam", priority="high", category="University",
             due_date=now + timedelta(days=2)),
        Task(title="Buy groceries", priority="low", category="Personal",
             due_date=now + timedelta(days=3)),
        Task(title="Prepare project presentation", priority="medium", category="University",
             due_date=now + timedelta(days=6)),
        Task(title="Read chapter 5", priority="low", category="University"),
        Task(title="Write Software Requirements Specification", priority="high",
             category="University", is_completed=True, completed_at=now - timedelta(days=2)),
        Task(title="Set up development environment", priority="medium", category="University",
             is_completed=True, completed_at=now - timedelta(days=1)),
        Task(title="Renew library card", priority="low", category="Personal",
             is_completed=True, completed_at=now - timedelta(days=20)),
    ]
    user.reminders = [
        Reminder(title="Team meeting", remind_at=now + timedelta(hours=5)),
        Reminder(title="Call the dentist", remind_at=now + timedelta(days=1)),
        Reminder(title="Pay the phone bill", remind_at=now + timedelta(days=4)),
        Reminder(title="Old reminder (already passed)", remind_at=now - timedelta(days=3)),
    ]
    user.notes = [
        Note(title="Flask application factory", category="Study",
             content="create_app() builds a new app, so tests can use their own settings.",
             updated_at=now - timedelta(hours=2)),
        Note(title="Project ideas", category="Personal",
             content="Add voice input and calendar sync after the project is finished.",
             updated_at=now - timedelta(days=1)),
        Note(title="Meeting notes", category="Work",
             content="Agreed to demonstrate the working dashboard next week.",
             updated_at=now - timedelta(days=3)),
    ]
    conversation = Conversation(title="Study help")
    conversation.messages = [
        Message(role="user", content="What is an ORM?"),
        Message(role="assistant", content="Sample text: an ORM maps database tables to classes."),
    ]
    user.conversations = [conversation]

    db.session.add(user)
    db.session.commit()
    return user


if __name__ == "__main__":
    app = create_app()
    if app.config.get("DEBUG") is not True:
        sys.exit("Demo data can only be added in the development configuration.")

    with app.app_context():
        demo = seed_demo_data()
        print(f"Created user '{demo.username}': {len(demo.tasks)} tasks, "
              f"{len(demo.reminders)} reminders, {len(demo.notes)} notes, "
              f"{len(demo.conversations)} conversation.")
