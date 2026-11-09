"""Day 19 - tests for in-app notifications."""

import re
from datetime import datetime, timedelta

import pytest
from sqlalchemy.exc import OperationalError

from app.models import Notification, Reminder, Task, User
from app.services.common import ITEMS_PER_PAGE
from app.services.notification_service import (
    LOOK_BACK,
    MAX_NEW_PER_CHECK,
    check_for_new_notifications,
    count_unread,
)
from app.utils import utc_now

NOW = datetime(2026, 11, 9, 12, 0)


def get_tester():
    return User.query.filter_by(username="tester").first()


def add(db, *records):
    db.session.add_all(records)
    db.session.commit()


def messages(user_id=None):
    query = Notification.query
    if user_id:
        query = query.filter_by(user_id=user_id)
    return [n.message for n in query.order_by(Notification.id)]


def page(client, path):
    return client.get(path).get_data(as_text=True)


# ---------- Which notifications are created ----------

def test_due_reminder_creates_a_notification(db, auth_client):
    add(db, Reminder(user=get_tester(), title="Call the bank", remind_at=NOW - timedelta(minutes=5)))
    assert check_for_new_notifications(get_tester().id, NOW) == 1
    notification = Notification.query.one()
    assert notification.message == "Reminder due: Call the bank"
    assert notification.link.startswith("/reminders?status=due")
    assert notification.is_read is False


def test_overdue_task_creates_a_notification(db, auth_client):
    add(db, Task(user=get_tester(), title="Submit report", due_date=NOW - timedelta(hours=1)))
    check_for_new_notifications(get_tester().id, NOW)
    notification = Notification.query.one()
    assert notification.message == "Task overdue: Submit report"
    assert notification.link.startswith("/tasks?status=overdue")


@pytest.mark.parametrize("record", [
    lambda u: Reminder(user=u, title="Future", remind_at=NOW + timedelta(minutes=1)),
    lambda u: Reminder(user=u, title="Dismissed", remind_at=NOW - timedelta(hours=1), is_notified=True),
    lambda u: Reminder(user=u, title="Too old", remind_at=NOW - LOOK_BACK - timedelta(minutes=1)),
    lambda u: Task(user=u, title="Not due yet", due_date=NOW + timedelta(minutes=1)),
    lambda u: Task(user=u, title="No date"),
    lambda u: Task(user=u, title="Finished", due_date=NOW - timedelta(hours=1), is_completed=True),
    lambda u: Task(user=u, title="Too old", due_date=NOW - LOOK_BACK - timedelta(minutes=1)),
])
def test_no_notification_for(db, auth_client, record):
    add(db, record(get_tester()))
    assert check_for_new_notifications(get_tester().id, NOW) == 0
    assert Notification.query.count() == 0


def test_same_thing_is_never_notified_twice(db, auth_client):
    add(db, Reminder(user=get_tester(), title="Once", remind_at=NOW - timedelta(minutes=5)))
    check_for_new_notifications(get_tester().id, NOW)
    check_for_new_notifications(get_tester().id, NOW + timedelta(minutes=1))
    assert Notification.query.count() == 1


def test_read_notification_is_not_created_again(db, auth_client):
    add(db, Reminder(user=get_tester(), title="Once", remind_at=NOW - timedelta(minutes=5)))
    check_for_new_notifications(get_tester().id, NOW)
    Notification.query.one().is_read = True
    db.session.commit()
    check_for_new_notifications(get_tester().id, NOW)
    assert Notification.query.count() == 1


def test_snoozed_reminder_gets_a_new_notification_at_its_new_time(db, auth_client):
    reminder = Reminder(user=get_tester(), title="Snoozed", remind_at=NOW - timedelta(minutes=5))
    add(db, reminder)
    check_for_new_notifications(get_tester().id, NOW)
    reminder.remind_at = NOW + timedelta(hours=1)
    db.session.commit()
    check_for_new_notifications(get_tester().id, NOW + timedelta(hours=2))
    assert messages() == ["Reminder due: Snoozed", "Reminder due: Snoozed"]


def test_notification_does_not_change_the_reminder(db, auth_client):
    """The reminder stays Due, so the Due list, dashboard warning and Snooze still work."""
    reminder = Reminder(user=get_tester(), title="Still due", remind_at=utc_now() - timedelta(minutes=5))
    add(db, reminder)
    check_for_new_notifications(get_tester().id)
    reminder = db.session.get(Reminder, reminder.id)
    assert reminder.is_notified is False
    assert reminder.status == "due"


def test_number_created_at_once_is_limited(db, auth_client):
    user = get_tester()
    add(db, *[Reminder(user=user, title=f"R{n}", remind_at=NOW - timedelta(minutes=n + 1))
              for n in range(MAX_NEW_PER_CHECK + 5)])
    assert check_for_new_notifications(user.id, NOW) == MAX_NEW_PER_CHECK
    assert check_for_new_notifications(user.id, NOW) == 5  # the rest come on the next page


def test_long_title_is_cut_to_fit(db, auth_client):
    # Forms allow 200 characters, but SQLite doesn't enforce lengths, so check the cut anyway
    add(db, Task(user=get_tester(), title="x" * 300, due_date=NOW - timedelta(minutes=1)))
    check_for_new_notifications(get_tester().id, NOW)
    assert len(Notification.query.one().message) == 255


def test_other_users_records_never_create_notifications_for_this_user(db, auth_client, make_user):
    alice = make_user("alice")
    add(db, Reminder(user=alice, title="ALICE", remind_at=NOW - timedelta(minutes=5)))
    assert check_for_new_notifications(get_tester().id, NOW) == 0
    assert check_for_new_notifications(alice.id, NOW) == 1
    assert messages(get_tester().id) == []


# ---------- Created when a page is opened ----------

def test_opening_any_page_creates_new_notifications(db, auth_client):
    add(db, Reminder(user=get_tester(), title="Due now", remind_at=utc_now() - timedelta(minutes=1)))
    auth_client.get("/tasks")
    assert messages() == ["Reminder due: Due now"]


def test_form_posts_and_visitors_do_not_run_the_check(db, client, auth_client):
    add(db, Reminder(user=get_tester(), title="Due now", remind_at=utc_now() - timedelta(minutes=1)))
    client.post("/notes/new", data={"title": "x"})
    assert Notification.query.count() == 0


def test_visitor_pages_still_work(client):
    assert client.get("/login").status_code == 200


# ---------- The bell in the header ----------

def test_bell_shows_the_unread_count(db, auth_client):
    user = get_tester()
    add(db, Notification(user=user, message="One"), Notification(user=user, message="Two"),
        Notification(user=user, message="Read", is_read=True))
    html = page(auth_client, "/")
    assert 'aria-label="Notifications, 2 unread"' in html
    assert re.search(r'app-unread-badge"[^>]*>2</span>', html)


def test_bell_has_no_badge_when_all_read(db, auth_client):
    html = page(auth_client, "/")
    assert 'aria-label="Notifications, 0 unread"' in html
    assert "app-unread-badge" not in html


def test_large_unread_count_is_shortened(db, auth_client):
    user = get_tester()
    add(db, *[Notification(user=user, message=str(n)) for n in range(120)])
    assert ">99+</span>" in page(auth_client, "/")


def test_bell_counts_only_the_users_own(db, auth_client, make_user):
    add(db, Notification(user=make_user("alice"), message="ALICE"))
    assert 'aria-label="Notifications, 0 unread"' in page(auth_client, "/")


def test_database_error_in_the_count_does_not_break_the_page(auth_client, monkeypatch):
    def broken(user_id):
        raise OperationalError("SELECT", {}, Exception("database is locked"))

    monkeypatch.setattr("app.navigation.count_unread", broken)
    response = auth_client.get("/settings")
    assert response.status_code == 200
    assert 'aria-label="Notifications, 0 unread"' in response.get_data(as_text=True)


# ---------- The list ----------

@pytest.mark.parametrize("method, path", [
    ("get", "/notifications"),
    ("post", "/notifications/1/open"),
    ("post", "/notifications/1/read"),
    ("post", "/notifications/read-all"),
])
def test_login_required(client, method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login")


def test_list_shows_unread_first_then_newest(db, auth_client):
    user = get_tester()
    add(db,
        Notification(user=user, message="Old unread", created_at=NOW - timedelta(days=2)),
        Notification(user=user, message="New read", is_read=True, created_at=NOW),
        Notification(user=user, message="New unread", created_at=NOW - timedelta(days=1)))
    html = page(auth_client, "/notifications")
    assert html.index("New unread") < html.index("Old unread") < html.index("New read")
    assert "2 unread" in html


def test_list_shows_only_the_users_own(db, auth_client, make_user):
    add(db, Notification(user=make_user("alice"), message="ALICE-SECRET"))
    assert "ALICE-SECRET" not in page(auth_client, "/notifications")


def test_empty_list_has_a_message(auth_client):
    assert "No notifications yet." in page(auth_client, "/notifications")


def test_menu_links_to_notifications(auth_client):
    assert re.search(r'nav-link active"\s+href="/notifications"', page(auth_client, "/notifications"))


def test_long_list_is_split_into_pages(db, auth_client):
    user = get_tester()
    add(db, *[Notification(user=user, message=f"N{n}") for n in range(ITEMS_PER_PAGE + 1)])
    assert "Page 1 of 2" in page(auth_client, "/notifications")


def test_message_with_html_is_shown_as_text(db, auth_client):
    add(db, Task(user=get_tester(), title="<script>alert(1)</script>", due_date=utc_now() - timedelta(minutes=1)))
    for path in ("/notifications", "/"):
        assert "<script>alert(1)</script>" not in page(auth_client, path)


# ---------- Opening and marking as read ----------

def test_open_marks_it_read_and_goes_to_its_page(db, auth_client):
    notification = Notification(user=get_tester(), message="Reminder due: X", link="/reminders?status=due")
    add(db, notification)
    response = auth_client.post(f"/notifications/{notification.id}/open")
    assert response.headers["Location"] == "/reminders?status=due"
    assert db.session.get(Notification, notification.id).is_read is True


def test_open_never_goes_to_another_website(db, auth_client):
    notification = Notification(user=get_tester(), message="Bad", link="https://evil.example/")
    add(db, notification)
    assert auth_client.post(f"/notifications/{notification.id}/open").headers["Location"] == "/notifications"


def test_link_from_a_real_notification_opens_the_filtered_list(db, auth_client):
    add(db, Task(user=get_tester(), title="Late", due_date=utc_now() - timedelta(minutes=1)))
    auth_client.get("/")
    link = Notification.query.one().link
    response = auth_client.get(link)
    assert response.status_code == 200
    assert "Late" in response.get_data(as_text=True)


def test_mark_one_as_read(db, auth_client):
    notification = Notification(user=get_tester(), message="One")
    add(db, notification)
    response = auth_client.post(f"/notifications/{notification.id}/read")
    assert response.headers["Location"] == "/notifications"
    assert count_unread(get_tester().id) == 0


def test_mark_all_as_read_only_changes_the_users_own(db, auth_client, make_user):
    alice, user = make_user("alice"), get_tester()
    add(db, Notification(user=user, message="A"), Notification(user=user, message="B"),
        Notification(user=alice, message="ALICE"))
    response = auth_client.post("/notifications/read-all", follow_redirects=True)
    assert "Marked 2 notifications as read." in response.get_data(as_text=True)
    assert count_unread(get_tester().id) == 0
    assert count_unread(alice.id) == 1


@pytest.mark.parametrize("action", ["open", "read"])
def test_another_users_notification_gives_404_and_stays_unread(db, auth_client, make_user, action):
    notification = Notification(user=make_user("alice"), message="ALICE", link="/")
    add(db, notification)
    assert auth_client.post(f"/notifications/{notification.id}/{action}").status_code == 404
    assert db.session.get(Notification, notification.id).is_read is False


@pytest.mark.parametrize("action", ["open", "read"])
def test_changes_cannot_be_made_by_a_link(db, auth_client, action):
    notification = Notification(user=get_tester(), message="One")
    add(db, notification)
    assert auth_client.get(f"/notifications/{notification.id}/{action}").status_code == 405
    assert db.session.get(Notification, notification.id).is_read is False


@pytest.mark.parametrize("path", ["/notifications/1/read", "/notifications/read-all"])
def test_changes_need_a_csrf_token(app, db, auth_client, path):
    add(db, Notification(user=get_tester(), message="One"))
    app.config["WTF_CSRF_ENABLED"] = True
    assert auth_client.post(path).status_code == 400
    assert count_unread(get_tester().id) == 1


def test_real_form_carries_a_working_csrf_token(app, db, auth_client):
    add(db, Notification(user=get_tester(), message="One"))
    app.config["WTF_CSRF_ENABLED"] = True
    html = page(auth_client, "/notifications")
    token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
    assert auth_client.post("/notifications/read-all", data={"csrf_token": token}).status_code == 302
    assert count_unread(get_tester().id) == 0
