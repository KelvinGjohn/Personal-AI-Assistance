"""Day 6 - tests for the dashboard data and page."""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app.models import Conversation, Note, Reminder, Task, User
from app.services.dashboard_service import get_dashboard_data, get_task_stats
from app.utils import datetime_short

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import seed_demo_data as seed  # noqa: E402

NOW = datetime(2026, 11, 2, 12, 0)  # A fixed time makes the results predictable


@pytest.fixture
def alice(make_user):
    return make_user("alice")


def add(db, *items):
    db.session.add_all(items)
    db.session.commit()


def test_task_stats_with_no_tasks_does_not_divide_by_zero(alice):
    stats = get_task_stats(alice.id, NOW)
    assert stats["total"] == 0
    assert stats["completion_rate"] == 0


def test_task_stats_counts_each_status(db, alice):
    add(db,
        Task(user=alice, title="Overdue", due_date=NOW - timedelta(days=1)),
        Task(user=alice, title="Future", due_date=NOW + timedelta(days=1)),
        Task(user=alice, title="No date"),
        Task(user=alice, title="Done recently", is_completed=True,
             completed_at=NOW - timedelta(days=1)),
        )
    stats = get_task_stats(alice.id, NOW)
    assert stats["total"] == 4
    assert stats["pending"] == 3
    assert stats["completed"] == 1
    assert stats["overdue"] == 1
    assert stats["completion_rate"] == 25


def test_completed_task_with_past_due_date_is_not_overdue(db, alice):
    add(db, Task(user=alice, title="Done late", due_date=NOW - timedelta(days=5),
                 is_completed=True, completed_at=NOW - timedelta(days=1)))
    assert get_task_stats(alice.id, NOW)["overdue"] == 0


def test_completed_this_week_ignores_older_tasks(db, alice):
    add(db,
        Task(user=alice, title="Recent", is_completed=True, completed_at=NOW - timedelta(days=6)),
        Task(user=alice, title="Old", is_completed=True, completed_at=NOW - timedelta(days=8)),
        )
    assert get_task_stats(alice.id, NOW)["completed_this_week"] == 1


def test_tasks_due_soon_order_and_overdue_flag(db, alice):
    add(db,
        Task(user=alice, title="Later", due_date=NOW + timedelta(days=3)),
        Task(user=alice, title="Late", due_date=NOW - timedelta(days=1)),
        Task(user=alice, title="No date"),
        Task(user=alice, title="Done", due_date=NOW + timedelta(days=1), is_completed=True),
        )
    items = get_dashboard_data(alice.id, NOW)["tasks_due_soon"]
    assert [(i["task"].title, i["is_overdue"]) for i in items] == [("Late", True), ("Later", False)]


def test_upcoming_reminders_exclude_past_and_are_sorted(db, alice):
    add(db,
        Reminder(user=alice, title="Past", remind_at=NOW - timedelta(hours=1)),
        Reminder(user=alice, title="Second", remind_at=NOW + timedelta(days=2)),
        Reminder(user=alice, title="First", remind_at=NOW + timedelta(hours=1)),
        )
    reminders = get_dashboard_data(alice.id, NOW)["upcoming_reminders"]
    assert [r.title for r in reminders] == ["First", "Second"]


def test_lists_are_limited_to_five_items(db, alice):
    add(db, *[Note(user=alice, title=f"Note {n}") for n in range(7)])
    assert len(get_dashboard_data(alice.id, NOW)["recent_notes"]) == 5


def test_recent_notes_newest_first(db, alice):
    add(db,
        Note(user=alice, title="Older", updated_at=NOW - timedelta(days=2)),
        Note(user=alice, title="Newer", updated_at=NOW - timedelta(hours=1)),
        )
    assert [n.title for n in get_dashboard_data(alice.id, NOW)["recent_notes"]] == ["Newer", "Older"]


def test_dashboard_data_never_includes_another_users_records(db, alice, make_user):
    bob = make_user("bob")
    add(db,
        Task(user=bob, title="Bob task", due_date=NOW + timedelta(days=1)),
        Reminder(user=bob, title="Bob reminder", remind_at=NOW + timedelta(days=1)),
        Note(user=bob, title="Bob note"),
        Conversation(user=bob, title="Bob chat"),
        )
    data = get_dashboard_data(alice.id, NOW)
    assert data["task_stats"]["total"] == 0
    assert data["tasks_due_soon"] == []
    assert data["upcoming_reminders"] == []
    assert data["recent_notes"] == []
    assert [card["value"] for card in data["summary_cards"]] == [0, 0, 0, 0]


def test_new_user_sees_empty_state(auth_client):
    html = auth_client.get("/").get_data(as_text=True)
    assert "Welcome, tester" in html
    assert "No upcoming reminders." in html
    assert "No notes yet." in html


def test_page_shows_real_data(db, client, login, alice):
    now = datetime.now() + timedelta(days=1)
    add(db,
        Task(user=alice, title="Write the report", priority="high", due_date=now),
        Reminder(user=alice, title="Call the bank", remind_at=now),
        Note(user=alice, title="Flask notes", content="Blueprints group routes", category="Study"),
        )
    login(client, "alice")
    html = client.get("/").get_data(as_text=True)
    for text in ("Write the report", "app-priority-high", "Call the bank",
                 "Flask notes", "Blueprints group routes", "Study"):
        assert text in html


def test_page_escapes_user_text(db, client, login, alice):
    """A note title containing HTML must be shown as text, never run as a script."""
    add(db, Note(user=alice, title="<script>alert(1)</script>"))
    login(client, "alice")
    html = client.get("/").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_datetime_short_filter():
    assert datetime_short(datetime(2026, 11, 3, 14, 30)) == "Tue 03 Nov 2026, 14:30 UTC"
    assert datetime_short(None) == ""


def test_seed_can_run_twice_and_leaves_other_users_alone(db, alice):
    seed.seed_demo_data()
    seed.seed_demo_data()

    assert User.query.filter_by(username="demo").count() == 1
    assert db.session.get(User, alice.id) is not None
    demo = User.query.filter_by(username="demo").first()
    assert len(demo.tasks) == 8
    assert Task.query.filter_by(user_id=demo.id).count() == 8


def test_seed_generates_a_new_working_password_each_time(db):
    first_user, first_password = seed.seed_demo_data()
    assert first_user.check_password(first_password)

    second_user, second_password = seed.seed_demo_data()
    assert second_password != first_password
    assert second_user.check_password(second_password)
    assert not second_user.check_password(first_password)
