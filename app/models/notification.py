"""Notification model: an in-app alert, e.g. "Reminder due: Submit report"."""

from app.extensions import db
from app.utils import utc_now


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    message = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255))  # page to open when clicked, e.g. "/reminders/3"
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    user = db.relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification {self.id} read={self.is_read}>"
