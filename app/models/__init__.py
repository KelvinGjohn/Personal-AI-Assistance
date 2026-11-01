"""
All database models.

Importing them here means `from app.models import User, Task` works, and that
SQLAlchemy knows about every table before db.create_all() runs.
"""

from app.models.user import User
from app.models.task import Task, PRIORITIES
from app.models.reminder import Reminder
from app.models.note import Note
from app.models.conversation import Conversation, Message
from app.models.notification import Notification

__all__ = ["User", "Task", "PRIORITIES", "Reminder", "Note",
           "Conversation", "Message", "Notification"]
