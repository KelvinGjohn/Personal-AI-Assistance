"""Reminder model: something to be reminded about at a specific date and time."""

from app.extensions import db
from app.utils import utc_now


class Reminder(db.Model):
    __tablename__ = "reminders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    remind_at = db.Column(db.DateTime, nullable=False, index=True)  # stored in UTC
    # True once the user has dismissed it. Setting a new time makes it False again.
    # Notifications don't change it: they keep their own record (notification_service.py).
    is_notified = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    user = db.relationship("User", back_populates="reminders")

    @property
    def status(self):
        """upcoming: still to come. due: waiting for the user. past: dismissed."""
        if self.remind_at > utc_now():
            return "upcoming"
        return "past" if self.is_notified else "due"

    def __repr__(self):
        return f"<Reminder {self.id} {self.title!r} at {self.remind_at}>"
