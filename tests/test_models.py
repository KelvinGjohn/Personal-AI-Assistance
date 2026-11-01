"""Day 4 - tests for the database models and relationships."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.models import Conversation, Message, Note, Notification, Reminder, Task, User


def test_all_tables_are_created(db):
    tables = set(inspect(db.engine).get_table_names())
    assert {"users", "tasks", "reminders", "notes",
            "conversations", "messages", "notifications"} <= tables


def test_create_user_with_defaults(make_user):
    user = make_user("alice")
    assert user.id is not None
    assert user.timezone == "UTC"
    assert user.created_at is not None


def test_username_and_email_must_be_unique(db, make_user):
    make_user("alice", "alice@example.com")
    db.session.add(User(username="alice", email="other@example.com", password_hash="x"))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()

    db.session.add(User(username="bob", email="alice@example.com", password_hash="x"))
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_task_defaults_and_relationship(db, make_user):
    user = make_user("alice")
    task = Task(user=user, title="Finish SRS")
    db.session.add(task)
    db.session.commit()

    assert task.priority == "medium"
    assert task.is_completed is False
    assert user.tasks == [task]
    assert task.user is user


def test_invalid_task_priority_is_rejected(db, make_user):
    user = make_user("alice")
    db.session.add(Task(user=user, title="Bad", priority="urgent"))
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_task_cannot_belong_to_missing_user(db):
    # Foreign keys are switched on, so user 999 must exist
    db.session.add(Task(user_id=999, title="Orphan"))
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_conversation_keeps_messages_in_order(db, make_user):
    user = make_user("alice")
    convo = Conversation(user=user, title="Study help")
    start = datetime(2026, 11, 1, 9, 0)
    convo.messages.append(Message(role="user", content="Hi", created_at=start))
    convo.messages.append(Message(role="assistant", content="Hello!",
                                  created_at=start + timedelta(seconds=2)))
    db.session.add(convo)
    db.session.commit()

    reloaded = db.session.get(Conversation, convo.id)
    assert [m.role for m in reloaded.messages] == ["user", "assistant"]


def test_invalid_message_role_is_rejected(db, make_user):
    convo = Conversation(user=make_user("alice"))
    convo.messages.append(Message(role="robot", content="?"))
    db.session.add(convo)
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_deleting_user_deletes_all_their_data(db, make_user):
    user = make_user("alice")
    convo = Conversation(user=user)
    convo.messages.append(Message(role="user", content="Hi"))
    db.session.add_all([
        Task(user=user, title="T"),
        Reminder(user=user, title="R", remind_at=datetime(2026, 12, 1, 9, 0)),
        Note(user=user, title="N", content="text"),
        Notification(user=user, message="M"),
        convo,
    ])
    db.session.commit()

    db.session.delete(user)
    db.session.commit()

    for model in (Task, Reminder, Note, Notification, Conversation, Message):
        assert db.session.query(model).count() == 0


def test_users_only_see_their_own_tasks(db, make_user):
    alice = make_user("alice")
    bob = make_user("bob")
    db.session.add_all([Task(user=alice, title="Alice task"), Task(user=bob, title="Bob task")])
    db.session.commit()

    # This filter_by(user_id=...) pattern is how every page will load private data
    alice_tasks = Task.query.filter_by(user_id=alice.id).all()
    assert [t.title for t in alice_tasks] == ["Alice task"]
