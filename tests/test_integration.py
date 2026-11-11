"""
Day 22 - integration tests: the modules working together.

The other test files check one module each. These follow a user through the
whole app using only the real pages and forms, the way a browser would.
"""

import re
from datetime import datetime, timedelta

import pytest

from app.models import Conversation, Message, Note, Notification, Reminder, Task, User
from app.utils import utc_now

PASSWORD = "integration-test-pass"  # Only ever used in the temporary test database

# Every page that needs a login
PAGES = ["/", "/tasks", "/tasks/new", "/reminders", "/reminders/new", "/notes", "/notes/new",
         "/chat/new", "/chat/history", "/calendar", "/calendar?view=day", "/search?q=bank",
         "/notifications", "/settings"]


def register(app, username):
    """A new browser that registers through the real form, which also logs it in."""
    client = app.test_client()
    response = client.post("/register", data={
        "username": username, "email": f"{username}@example.com",
        "password": PASSWORD, "confirm_password": PASSWORD,
    })
    assert response.status_code == 302
    return client


def page(client, path):
    response = client.get(path, follow_redirects=True)
    assert response.status_code == 200, path
    return response.get_data(as_text=True)


def add_everything(client, word="bank"):
    """One task, one reminder, one note and one chat, each made with its own form."""
    assert client.post("/tasks/new", data={
        "title": f"Pay the {word}", "priority": "high", "due_date": "2099-03-10T14:00",
    }).status_code == 302
    assert client.post("/reminders/new", data={
        "title": f"Call the {word}", "remind_at": "2099-03-10T09:00",
    }).status_code == 302
    assert client.post("/notes/new", data={
        "title": f"{word.capitalize()} details", "content": "Opening hours 9 to 5",
    }).status_code == 302
    assert client.post("/chat/new", data={"message": f"Explain {word} interest"}).status_code == 302


def card_value(html, label):
    """The big number on a dashboard summary card."""
    match = re.search(re.escape(label) + r'</p>\s*<p class="h4 mb-0">(\d+)</p>', html)
    return int(match.group(1))


# ---------- One user, every module ----------

def test_new_records_appear_on_every_page_that_should_show_them(app):
    client = register(app, "kelvin")
    add_everything(client)

    dashboard = page(client, "/")
    assert card_value(dashboard, "Pending tasks") == 1
    assert card_value(dashboard, "Upcoming reminders") == 1
    assert card_value(dashboard, "Notes") == 1
    assert card_value(dashboard, "Conversations") == 1
    for title in ("Pay the bank", "Call the bank", "Bank details"):
        assert title in dashboard

    search = page(client, "/search?q=BANK")
    assert "4 results" in search
    for label in ("Tasks (1)", "Reminders (1)", "Notes (1)", "Chats (1)"):
        assert label in search

    day = page(client, "/calendar?view=day&date=2099-03-10")
    assert "2 items" in day
    assert day.index("Call the bank") < day.index("Pay the bank")  # 09:00 before 14:00

    assert "Pay the bank" in page(client, "/tasks")
    assert "Call the bank" in page(client, "/reminders")
    assert "Bank details" in page(client, "/notes")
    assert "Explain bank interest" in page(client, "/chat")


def test_dashboard_links_lead_to_the_records(app):
    client = register(app, "kelvin")
    add_everything(client)
    task, reminder, note = Task.query.one(), Reminder.query.one(), Note.query.one()

    dashboard = page(client, "/")
    for link in (f"/tasks/{task.id}/edit", f"/reminders/{reminder.id}/edit", f"/notes/{note.id}",
                 "/tasks", "/reminders", "/notes", "/chat/history", "/calendar?view=day"):
        assert f'href="{link}"' in dashboard
        page(client, link)  # and each link opens


def test_search_and_calendar_results_open_the_right_record(app):
    client = register(app, "kelvin")
    add_everything(client)
    task = Task.query.one()

    for source in ("/search?q=bank", "/calendar?view=week&date=2099-03-10"):
        assert f'href="/tasks/{task.id}/edit"' in page(client, source)
    assert 'value="Pay the bank"' in page(client, f"/tasks/{task.id}/edit")


def test_time_passing_creates_notifications_that_lead_back_to_the_records(app, db):
    client = register(app, "kelvin")
    add_everything(client)
    assert "app-unread-badge" not in page(client, "/")

    # Time passes: both are now an hour in the past
    Task.query.one().due_date = utc_now() - timedelta(hours=1)
    Reminder.query.one().remind_at = utc_now() - timedelta(hours=1)
    db.session.commit()

    dashboard = page(client, "/")
    assert re.search(r'app-unread-badge"[^>]*>2</span>', dashboard)
    assert "You have 1 reminder due." in dashboard
    assert "1 overdue" in dashboard
    assert "2 items on today" in dashboard

    notifications = page(client, "/notifications")
    assert "Call the bank" in notifications and "Pay the bank" in notifications

    for notification in Notification.query.all():
        response = client.post(f"/notifications/{notification.id}/open")
        assert response.status_code == 302
        assert response.headers["Location"].startswith(("/reminders", "/tasks"))
        page(client, response.headers["Location"])
    assert "app-unread-badge" not in page(client, "/")


def test_finishing_a_task_updates_every_page(app, db):
    client = register(app, "kelvin")
    add_everything(client)
    task = Task.query.one()
    task.due_date = utc_now() - timedelta(hours=1)
    db.session.commit()
    task_id = task.id
    today = utc_now().date().isoformat()

    assert "1 overdue" in page(client, "/")
    assert client.post(f"/tasks/{task_id}/complete").status_code == 302

    dashboard = page(client, "/")
    assert card_value(dashboard, "Pending tasks") == 0
    assert "0 overdue" in dashboard
    assert "100%" in dashboard
    assert "Pay the bank" not in dashboard.split("Tasks due soon")[1].split("Upcoming reminders")[0]
    assert re.search(r'app-item-done"\s+href="[^"]+">Pay the bank<',
                     page(client, f"/calendar?view=day&date={today}"))
    assert "Pay the bank" in page(client, "/search?q=pay")  # finished tasks can still be found

    # And reopening it puts it back
    assert client.post(f"/tasks/{task_id}/reopen").status_code == 302
    assert card_value(page(client, "/"), "Pending tasks") == 1


def test_editing_a_record_changes_it_everywhere(app):
    client = register(app, "kelvin")
    add_everything(client)
    task = Task.query.one()

    assert client.post(f"/tasks/{task.id}/edit", data={
        "title": "Visit the branch", "priority": "low", "due_date": "2099-03-12T10:00",
    }).status_code == 302

    assert "Visit the branch" in page(client, "/")
    assert "Visit the branch" in page(client, "/search?q=branch")
    assert "Pay the bank" not in page(client, "/search?q=bank&type=tasks")
    assert "Visit the branch" not in page(client, "/calendar?view=day&date=2099-03-10")
    assert "Visit the branch" in page(client, "/calendar?view=day&date=2099-03-12")


def test_deleted_records_disappear_from_every_page(app):
    client = register(app, "kelvin")
    add_everything(client)
    task, reminder, note, chat = (Task.query.one(), Reminder.query.one(), Note.query.one(),
                                  Conversation.query.one())

    for path in (f"/tasks/{task.id}/delete", f"/reminders/{reminder.id}/delete",
                 f"/notes/{note.id}/delete", f"/chat/{chat.id}/delete"):
        assert client.post(path).status_code == 302

    dashboard = page(client, "/")
    for label in ("Pending tasks", "Upcoming reminders", "Notes", "Conversations"):
        assert card_value(dashboard, label) == 0
    assert "0 results" in page(client, "/search?q=bank")
    assert "0 items" in page(client, "/calendar?view=day&date=2099-03-10")
    assert Message.query.count() == 0  # the chat's messages went with it


def test_calendar_day_opens_new_forms_with_that_day_filled_in(app):
    client = register(app, "kelvin")
    day = page(client, "/calendar?view=day&date=2099-03-10")
    assert 'href="/tasks/new?date=2099-03-10"' in day
    assert 'href="/reminders/new?date=2099-03-10"' in day
    assert 'value="2099-03-10T09:00"' in page(client, "/tasks/new?date=2099-03-10")
    assert 'value="2099-03-10T09:00"' in page(client, "/reminders/new?date=2099-03-10")

    # Saving that form puts the record on that calendar day
    assert client.post("/tasks/new", data={
        "title": "Dentist", "priority": "medium", "due_date": "2099-03-10T09:00",
    }).status_code == 302
    assert "Dentist" in page(client, "/calendar?view=day&date=2099-03-10")


@pytest.mark.parametrize("date", ["", "nonsense", "9999-12-31", "2026-02-30", "<script>"])
@pytest.mark.parametrize("form", ["/tasks/new", "/reminders/new"])
def test_new_forms_ignore_a_bad_date_in_the_address(app, form, date):
    client = register(app, "kelvin")
    html = client.get(form, query_string={"date": date}).get_data(as_text=True)
    assert not re.search(r'type="datetime-local"[^>]*value="\d', html)
    assert "<script>" not in html.split("<main")[1].split("</main>")[0]


def test_changing_the_time_zone_changes_every_page(app, db):
    client = register(app, "kelvin")
    db.session.add(Reminder(user=User.query.one(), title="Late call",
                            remind_at=datetime(2099, 3, 10, 22, 0)))  # stored in UTC
    db.session.commit()
    assert "22:00" in page(client, "/calendar?view=day&date=2099-03-10")

    assert client.post("/settings", data={
        "email": "kelvin@example.com", "timezone": "Asia/Tokyo", "save_profile": "Save changes",
    }).status_code == 302

    # 22:00 UTC on the 10th is 07:00 on the 11th in Tokyo
    assert "Late call" not in page(client, "/calendar?view=day&date=2099-03-10")
    assert "07:00" in page(client, "/calendar?view=day&date=2099-03-11")
    for path in ("/", "/reminders", "/search?q=late"):
        assert "Wed 11 Mar 2099, 07:00 JST" in page(client, path), path


# ---------- Two users ----------

def test_two_users_never_see_each_others_data_on_any_page(app):
    alice = register(app, "alice")
    add_everything(alice, word="zebra")
    bob = register(app, "bob")

    for path in PAGES + ["/calendar?view=day&date=2099-03-10", "/calendar?view=week&date=2099-03-10"]:
        assert "zebra" not in page(bob, path).lower(), path
    # The search page repeats the word Bob typed, so check its count instead
    assert "0 results" in page(bob, "/search?q=zebra")
    dashboard = page(bob, "/")
    for label in ("Pending tasks", "Upcoming reminders", "Notes", "Conversations"):
        assert card_value(dashboard, label) == 0

    # Alice still has everything
    assert "4 results" in page(alice, "/search?q=zebra")


def test_another_users_records_cannot_be_opened_changed_or_deleted(app):
    alice = register(app, "alice")
    add_everything(alice)
    bob = register(app, "bob")
    task, reminder, note, chat = (Task.query.one(), Reminder.query.one(), Note.query.one(),
                                  Conversation.query.one())

    for path in (f"/tasks/{task.id}/edit", f"/tasks/{task.id}/delete", f"/reminders/{reminder.id}/edit",
                 f"/reminders/{reminder.id}/delete", f"/notes/{note.id}", f"/notes/{note.id}/edit",
                 f"/notes/{note.id}/delete", f"/chat/{chat.id}", f"/chat/{chat.id}/rename",
                 f"/chat/{chat.id}/delete"):
        assert bob.get(path).status_code == 404, path
    for path in (f"/tasks/{task.id}/complete", f"/tasks/{task.id}/delete", f"/reminders/{reminder.id}/dismiss",
                 f"/reminders/{reminder.id}/delete", f"/notes/{note.id}/delete", f"/chat/{chat.id}/delete"):
        assert bob.post(path).status_code == 404, path
    assert bob.post(f"/chat/{chat.id}", data={"message": "Let me in"}).status_code == 404

    # Nothing of Alice's changed
    assert (Task.query.count(), Reminder.query.count(), Note.query.count(), Conversation.query.count()) == (1, 1, 1, 1)
    assert Task.query.one().is_completed is False
    assert Message.query.filter_by(content="Let me in").count() == 0


def test_one_users_due_items_do_not_notify_the_other(app, db):
    alice = register(app, "alice")
    add_everything(alice)
    bob = register(app, "bob")
    Reminder.query.one().remind_at = utc_now() - timedelta(hours=1)
    db.session.commit()

    assert "app-unread-badge" not in page(bob, "/")
    assert re.search(r'app-unread-badge"[^>]*>1</span>', page(alice, "/"))


# ---------- Logging out, and deleting an account ----------

def test_after_logging_out_every_page_asks_for_a_login(app):
    client = register(app, "kelvin")
    add_everything(client)
    for path in PAGES:
        page(client, path)  # all open while logged in

    assert client.post("/logout").status_code == 302
    for path in PAGES:
        response = client.get(path)
        assert response.status_code == 302, path
        assert response.headers["Location"].startswith("/login"), path


def test_logging_back_in_shows_the_same_data(app):
    client = register(app, "kelvin")
    add_everything(client)
    client.post("/logout")
    assert client.post("/login", data={"identifier": "kelvin", "password": PASSWORD}).status_code == 302
    assert "4 results" in page(client, "/search?q=bank")


def test_deleting_a_user_removes_all_of_their_data_and_nobody_elses(app, db):
    alice = register(app, "alice")
    add_everything(alice)
    bob = register(app, "bob")
    add_everything(bob)
    Reminder.query.filter_by(user_id=User.query.filter_by(username="alice").one().id).one().remind_at = \
        utc_now() - timedelta(hours=1)
    db.session.commit()
    page(alice, "/")  # creates Alice's notification
    assert Notification.query.count() == 1

    db.session.delete(User.query.filter_by(username="alice").one())
    db.session.commit()

    bob_id = User.query.one().id
    for model in (Task, Reminder, Note, Conversation):
        assert [record.user_id for record in model.query.all()] == [bob_id]
    assert Notification.query.count() == 0
    assert Message.query.count() == Message.query.join(Conversation).filter(Conversation.user_id == bob_id).count()
    assert "4 results" in page(bob, "/search?q=bank")
