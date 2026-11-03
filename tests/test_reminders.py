"""Day 10 - tests for the reminder module and due detection."""

import re
from datetime import datetime, timedelta

import pytest

from app.models import Reminder, User
from app.services.common import ITEMS_PER_PAGE
from app.services.reminder_service import (
    SNOOZE_TIME,
    build_reminder_query,
    count_due_reminders,
)
from app.utils import utc_now

FUTURE = datetime(2099, 1, 15, 12, 0)
NOW = datetime(2026, 11, 4, 12, 0)


def get_tester():
    return User.query.filter_by(username="tester").first()


def add_reminder(db, user=None, **fields):
    fields.setdefault("title", "A reminder")
    fields.setdefault("remind_at", FUTURE)
    reminder = Reminder(user=user or get_tester(), **fields)
    db.session.add(reminder)
    db.session.commit()
    return reminder


def post_reminder(client, path="/reminders/new", **overrides):
    data = {"title": "Call the bank", "description": "", "remind_at": "2099-01-15T12:00"}
    data.update(overrides)
    return client.post(path, data=data)


def page(client, path="/reminders"):
    return client.get(path).get_data(as_text=True)


def form_time(value):
    return value.strftime("%Y-%m-%dT%H:%M")


# ---------- Login required ----------

@pytest.mark.parametrize("method, path", [
    ("get", "/reminders"),
    ("get", "/reminders/new"),
    ("post", "/reminders/new"),
    ("get", "/reminders/1/edit"),
    ("post", "/reminders/1/dismiss"),
    ("post", "/reminders/1/snooze"),
    ("post", "/reminders/1/delete"),
])
def test_every_reminder_page_requires_login(client, method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login")


# ---------- Create ----------

def test_create_reminder(auth_client):
    response = post_reminder(auth_client, title="  Call the bank ", description="About the card")
    assert response.status_code == 302
    reminder = Reminder.query.one()
    assert reminder.user_id == get_tester().id
    assert reminder.title == "Call the bank"
    assert reminder.description == "About the card"
    assert reminder.remind_at == FUTURE
    assert reminder.is_notified is False


def test_empty_description_is_saved_as_null(auth_client):
    post_reminder(auth_client)
    assert Reminder.query.one().description is None


def test_time_typed_in_user_zone_is_saved_as_utc(db, auth_client):
    get_tester().timezone = "Europe/Paris"
    db.session.commit()
    post_reminder(auth_client, remind_at="2099-07-15T14:00")
    assert Reminder.query.one().remind_at == datetime(2099, 7, 15, 12, 0)


@pytest.mark.parametrize("overrides, message", [
    ({"title": ""}, "Enter a title."),
    ({"title": "   "}, "Enter a title."),
    ({"title": "x" * 201}, "200 characters or fewer"),
    ({"description": "x" * 5001}, "5000 characters or fewer"),
    ({"remind_at": ""}, "Enter a valid date and time."),
    ({"remind_at": "not-a-date"}, "Enter a valid date and time."),
    ({"remind_at": "2020-01-01T09:00"}, "Choose a time in the future."),
    ({"remind_at": "0001-01-01T00:00"}, "between 2000 and 2100"),
    ({"remind_at": "9999-12-31T23:59"}, "between 2000 and 2100"),
])
def test_invalid_reminder_is_rejected(auth_client, overrides, message):
    response = post_reminder(auth_client, **overrides)
    assert response.status_code == 200
    assert message in response.get_data(as_text=True)
    assert Reminder.query.count() == 0


def test_future_check_uses_the_users_time_zone(db, auth_client):
    # Tokyo is 9 hours ahead of UTC, so this clock time was an hour ago there,
    # although read as UTC it would look 8 hours in the future
    get_tester().timezone = "Asia/Tokyo"
    db.session.commit()
    typed = utc_now() + timedelta(hours=8)
    response = post_reminder(auth_client, remind_at=form_time(typed))
    assert "Choose a time in the future." in response.get_data(as_text=True)
    assert Reminder.query.count() == 0


def test_form_cannot_set_the_owner_or_notified_flag(auth_client, make_user):
    alice = make_user("alice")
    post_reminder(auth_client, user_id=alice.id, is_notified="y")
    reminder = Reminder.query.one()
    assert reminder.user_id == get_tester().id
    assert reminder.is_notified is False


# ---------- Status and due detection ----------

@pytest.mark.parametrize("offset, is_notified, expected", [
    (timedelta(minutes=1), False, "upcoming"),
    (timedelta(minutes=-1), False, "due"),
    (timedelta(minutes=-1), True, "past"),
])
def test_status(db, auth_client, offset, is_notified, expected):
    reminder = add_reminder(db, remind_at=utc_now() + offset, is_notified=is_notified)
    assert reminder.status == expected


def test_reminder_is_due_at_exactly_its_time(db, auth_client):
    add_reminder(db, remind_at=NOW)
    assert count_due_reminders(get_tester().id, NOW) == 1
    assert count_due_reminders(get_tester().id, NOW - timedelta(seconds=1)) == 0


def test_due_count_ignores_dismissed_upcoming_and_other_users(db, auth_client, make_user):
    alice = make_user("alice")
    add_reminder(db, title="Due", remind_at=NOW - timedelta(hours=1))
    add_reminder(db, title="Dismissed", remind_at=NOW - timedelta(hours=1), is_notified=True)
    add_reminder(db, title="Upcoming", remind_at=NOW + timedelta(hours=1))
    add_reminder(db, user=alice, title="Alice due", remind_at=NOW - timedelta(hours=1))
    assert count_due_reminders(get_tester().id, NOW) == 1


def test_order_is_due_then_upcoming_then_past(db, auth_client):
    add_reminder(db, title="past", remind_at=NOW - timedelta(days=5), is_notified=True)
    add_reminder(db, title="upcoming-later", remind_at=NOW + timedelta(days=2))
    add_reminder(db, title="upcoming-soon", remind_at=NOW + timedelta(days=1))
    add_reminder(db, title="due-recent", remind_at=NOW - timedelta(hours=1))
    add_reminder(db, title="due-old", remind_at=NOW - timedelta(days=1))
    reminders = build_reminder_query(get_tester().id, now=NOW).all()
    assert [r.title for r in reminders] == [
        "due-old", "due-recent", "upcoming-soon", "upcoming-later", "past",
    ]


def test_past_only_list_shows_most_recent_first(db, auth_client):
    add_reminder(db, title="older", remind_at=NOW - timedelta(days=5), is_notified=True)
    add_reminder(db, title="newer", remind_at=NOW - timedelta(days=1), is_notified=True)
    reminders = build_reminder_query(get_tester().id, "past", NOW).all()
    assert [r.title for r in reminders] == ["newer", "older"]


# ---------- Filters ----------

@pytest.fixture
def mixed_reminders(db, auth_client):
    now = utc_now()
    add_reminder(db, title="Due one", remind_at=now - timedelta(hours=1))
    add_reminder(db, title="Upcoming one", remind_at=now + timedelta(hours=1))
    add_reminder(db, title="Past one", remind_at=now - timedelta(hours=2), is_notified=True)
    return auth_client


def titles(html):
    return [t for t in ("Due one", "Upcoming one", "Past one") if t in html]


@pytest.mark.parametrize("query, expected", [
    ("", ["Due one", "Upcoming one", "Past one"]),
    ("?status=due", ["Due one"]),
    ("?status=upcoming", ["Upcoming one"]),
    ("?status=past", ["Past one"]),
    ("?status=nonsense", ["Due one", "Upcoming one", "Past one"]),
])
def test_filters(mixed_reminders, query, expected):
    assert titles(page(mixed_reminders, "/reminders" + query)) == expected


def test_due_count_is_shown_on_the_filter(mixed_reminders):
    assert re.search(r"Due \(1\)", page(mixed_reminders))


def test_empty_filter_shows_a_message(db, auth_client):
    add_reminder(db)
    assert "No past reminders." in page(auth_client, "/reminders?status=past")


def test_only_due_reminders_have_dismiss_and_snooze_buttons(mixed_reminders):
    html = page(mixed_reminders)
    assert html.count("/dismiss") == 1
    assert html.count("/snooze") == 1
    assert "Dismiss: Due one" in html


# ---------- Dismiss and snooze ----------

def test_dismiss_moves_a_due_reminder_to_past(db, auth_client):
    reminder = add_reminder(db, remind_at=utc_now() - timedelta(hours=1))
    assert auth_client.post(f"/reminders/{reminder.id}/dismiss").status_code == 302
    assert db.session.get(Reminder, reminder.id).status == "past"


def test_dismiss_does_nothing_to_an_upcoming_reminder(db, auth_client):
    reminder = add_reminder(db)
    auth_client.post(f"/reminders/{reminder.id}/dismiss")
    assert db.session.get(Reminder, reminder.id).is_notified is False


def test_snooze_moves_a_due_reminder_forward(db, auth_client):
    reminder = add_reminder(db, remind_at=utc_now() - timedelta(hours=1))
    before = utc_now()
    assert auth_client.post(f"/reminders/{reminder.id}/snooze").status_code == 302
    reminder = db.session.get(Reminder, reminder.id)
    assert reminder.status == "upcoming"
    assert before + SNOOZE_TIME <= reminder.remind_at <= utc_now() + SNOOZE_TIME


@pytest.mark.parametrize("fields", [
    {"remind_at": FUTURE},
    {"remind_at": datetime(2020, 1, 1), "is_notified": True},
])
def test_snooze_does_nothing_unless_due(db, auth_client, fields):
    reminder = add_reminder(db, **fields)
    auth_client.post(f"/reminders/{reminder.id}/snooze")
    assert db.session.get(Reminder, reminder.id).remind_at == fields["remind_at"]


@pytest.mark.parametrize("action", ["dismiss", "snooze"])
def test_buttons_cannot_be_triggered_by_a_link(db, auth_client, action):
    reminder = add_reminder(db, remind_at=datetime(2020, 1, 1))
    assert auth_client.get(f"/reminders/{reminder.id}/{action}").status_code == 405
    assert db.session.get(Reminder, reminder.id).status == "due"


def test_dismiss_returns_to_the_filtered_list(db, auth_client):
    reminder = add_reminder(db, remind_at=datetime(2020, 1, 1))
    response = auth_client.post(f"/reminders/{reminder.id}/dismiss", data={"next": "/reminders?status=due"})
    assert response.headers["Location"] == "/reminders?status=due"


def test_dismiss_ignores_next_pointing_to_another_site(db, auth_client):
    reminder = add_reminder(db, remind_at=datetime(2020, 1, 1))
    response = auth_client.post(f"/reminders/{reminder.id}/dismiss", data={"next": "//evil.example"})
    assert response.headers["Location"] == "/reminders"


# ---------- Edit ----------

def test_edit_form_is_filled_in_the_users_time_zone(db, auth_client):
    get_tester().timezone = "Asia/Tokyo"
    reminder = add_reminder(db, title="Original", description="Details")
    html = page(auth_client, f"/reminders/{reminder.id}/edit")
    assert 'value="Original"' in html
    assert "Details" in html
    assert 'value="2099-01-15T21:00"' in html


def test_edit_saves_changes(db, auth_client):
    reminder = add_reminder(db, title="Original", description="Details")
    response = post_reminder(auth_client, f"/reminders/{reminder.id}/edit", title="Changed",
                             remind_at="2099-02-01T08:30")
    assert response.status_code == 302
    reminder = db.session.get(Reminder, reminder.id)
    assert reminder.title == "Changed"
    assert reminder.description is None
    assert reminder.remind_at == datetime(2099, 2, 1, 8, 30)


def test_old_reminder_can_be_edited_without_changing_its_time(db, auth_client):
    old_time = datetime(2020, 1, 1, 9, 0, 45)  # seconds, which a form can't hold
    reminder = add_reminder(db, remind_at=old_time, is_notified=True)
    response = post_reminder(auth_client, f"/reminders/{reminder.id}/edit", title="Typo fixed",
                             remind_at="2020-01-01T09:00")
    assert response.status_code == 302
    reminder = db.session.get(Reminder, reminder.id)
    assert reminder.title == "Typo fixed"
    assert reminder.remind_at == old_time
    assert reminder.is_notified is True  # it must not go off again


def test_edit_cannot_move_a_time_to_another_past_time(db, auth_client):
    reminder = add_reminder(db, remind_at=datetime(2020, 1, 1, 9, 0))
    response = post_reminder(auth_client, f"/reminders/{reminder.id}/edit", remind_at="2021-01-01T09:00")
    assert "Choose a time in the future." in response.get_data(as_text=True)
    assert db.session.get(Reminder, reminder.id).remind_at == datetime(2020, 1, 1, 9, 0)


def test_new_time_makes_a_dismissed_reminder_go_off_again(db, auth_client):
    reminder = add_reminder(db, remind_at=datetime(2020, 1, 1), is_notified=True)
    post_reminder(auth_client, f"/reminders/{reminder.id}/edit", remind_at="2099-01-01T09:00")
    reminder = db.session.get(Reminder, reminder.id)
    assert reminder.is_notified is False
    assert reminder.status == "upcoming"


def test_invalid_edit_changes_nothing(db, auth_client):
    reminder = add_reminder(db, title="Original")
    response = post_reminder(auth_client, f"/reminders/{reminder.id}/edit", title="")
    assert "Enter a title." in response.get_data(as_text=True)
    assert db.session.get(Reminder, reminder.id).title == "Original"


# ---------- Delete ----------

def test_get_only_asks_and_post_deletes(db, auth_client):
    reminder = add_reminder(db, title="Remove me")
    assert 'Delete "Remove me"?' in page(auth_client, f"/reminders/{reminder.id}/delete")
    assert Reminder.query.count() == 1

    assert auth_client.post(f"/reminders/{reminder.id}/delete").status_code == 302
    assert Reminder.query.count() == 0


# ---------- One user can't reach another user's reminders ----------

@pytest.mark.parametrize("method, action", [
    ("get", "edit"),
    ("post", "edit"),
    ("post", "dismiss"),
    ("post", "snooze"),
    ("get", "delete"),
    ("post", "delete"),
])
def test_another_users_reminder_gives_404_and_stays_unchanged(db, auth_client, make_user, method, action):
    alice = make_user("alice")
    old_time = datetime(2020, 1, 1)
    reminder = add_reminder(db, user=alice, title="Alice private", remind_at=old_time)
    response = getattr(auth_client, method)(f"/reminders/{reminder.id}/{action}", data={"title": "Hacked"})
    assert response.status_code == 404
    assert "Alice private" not in response.get_data(as_text=True)

    reminder = db.session.get(Reminder, reminder.id)
    assert reminder.title == "Alice private"
    assert reminder.remind_at == old_time
    assert reminder.is_notified is False


def test_list_shows_only_own_reminders(db, auth_client, make_user):
    add_reminder(db, user=make_user("alice"), title="Alice private")
    add_reminder(db, title="My reminder")
    html = page(auth_client)
    assert "My reminder" in html
    assert "Alice private" not in html


@pytest.mark.parametrize("path", ["/reminders/999/edit", "/reminders/99999999999999999999/edit"])
def test_id_that_does_not_exist_gives_404(auth_client, path):
    assert auth_client.get(path).status_code == 404


# ---------- Pages ----------

def test_long_lists_are_split_into_pages_and_keep_filters(db, auth_client):
    user = get_tester()
    db.session.add_all([Reminder(user=user, title=f"R {n}", remind_at=FUTURE)
                        for n in range(ITEMS_PER_PAGE + 1)])
    db.session.commit()

    html = page(auth_client, "/reminders?status=upcoming")
    assert html.count('class="list-group-item app-item"') == ITEMS_PER_PAGE
    assert "Page 1 of 2" in html
    assert "page=2" in html and "status=upcoming" in html

    html = page(auth_client, "/reminders?status=upcoming&page=2")
    assert html.count('class="list-group-item app-item"') == 1


@pytest.mark.parametrize("number", ["0", "-5", "999", "99999999999999999999999", "abc"])
def test_bad_page_numbers_are_corrected(db, auth_client, number):
    add_reminder(db, title="Still shown")
    response = auth_client.get(f"/reminders?page={number}")
    assert response.status_code == 200
    assert "Still shown" in response.get_data(as_text=True)


# ---------- Display, dashboard and safety ----------

def test_new_user_sees_the_empty_message(auth_client):
    assert "You have no reminders yet." in page(auth_client)


def test_times_are_shown_in_the_users_time_zone(db, auth_client):
    get_tester().timezone = "Asia/Tokyo"
    add_reminder(db)
    assert "Thu 15 Jan 2099, 21:00 JST" in page(auth_client)


def test_user_text_is_shown_as_text_not_run(auth_client):
    bad = "<script>alert(1)</script>"
    post_reminder(auth_client, title=bad, description=bad)
    reminder = Reminder.query.one()
    for path in ("/reminders", "/", f"/reminders/{reminder.id}/edit", f"/reminders/{reminder.id}/delete"):
        assert bad not in page(auth_client, path)


def test_menu_links_to_reminders_and_highlights_it(auth_client):
    html = page(auth_client, "/reminders/new")
    assert re.search(r'nav-link active"\s+href="/reminders"', html)


def test_dashboard_warns_about_due_reminders(db, auth_client):
    add_reminder(db, remind_at=utc_now() - timedelta(hours=1))
    add_reminder(db, remind_at=utc_now() - timedelta(hours=2))
    html = page(auth_client, "/")
    assert "You have 2 reminders due." in html
    assert "/reminders?status=due" in html


def test_dashboard_wording_for_one_due_reminder(db, auth_client):
    add_reminder(db, remind_at=utc_now() - timedelta(hours=1))
    assert "You have 1 reminder due." in page(auth_client, "/")


def test_dashboard_has_no_warning_when_nothing_is_due(db, auth_client):
    add_reminder(db)
    add_reminder(db, remind_at=utc_now() - timedelta(hours=1), is_notified=True)
    assert "reminder due" not in page(auth_client, "/")
    assert "reminders due" not in page(auth_client, "/")


# ---------- CSRF ----------

@pytest.mark.parametrize("action", ["dismiss", "snooze", "delete", "edit"])
def test_changes_without_csrf_token_are_rejected(app, db, auth_client, action):
    reminder = add_reminder(db, title="Protected", remind_at=datetime(2020, 1, 1))
    app.config["WTF_CSRF_ENABLED"] = True
    assert auth_client.post(f"/reminders/{reminder.id}/{action}").status_code == 400
    reminder = db.session.get(Reminder, reminder.id)
    assert reminder.title == "Protected"
    assert reminder.status == "due"


def test_real_forms_carry_working_csrf_tokens(app, db, auth_client):
    reminder = add_reminder(db, remind_at=datetime(2020, 1, 1))
    app.config["WTF_CSRF_ENABLED"] = True
    token = re.search(r'name="csrf_token" value="([^"]+)"', page(auth_client)).group(1)
    response = auth_client.post(f"/reminders/{reminder.id}/dismiss", data={"csrf_token": token})
    assert response.status_code == 302
    assert db.session.get(Reminder, reminder.id).status == "past"
