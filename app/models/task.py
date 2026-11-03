"""Task model: a to-do item belonging to one user."""

from app.extensions import db
from app.utils import utc_now

PRIORITIES = ("low", "medium", "high")


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    priority = db.Column(db.String(10), nullable=False, default="medium")
    category = db.Column(db.String(50))
    due_date = db.Column(db.DateTime)
    is_completed = db.Column(db.Boolean, nullable=False, default=False)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    user = db.relationship("User", back_populates="tasks")

    # The database itself rejects any priority other than low / medium / high
    __table_args__ = (
        db.CheckConstraint("priority IN ('low', 'medium', 'high')", name="ck_task_priority"),
    )

    @property
    def is_overdue(self):
        """Not finished, and the due date has already passed."""
        return bool(not self.is_completed and self.due_date and self.due_date < utc_now())

    def __repr__(self):
        return f"<Task {self.id} {self.title!r}>"
