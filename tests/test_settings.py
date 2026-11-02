"""Day 8 - tests for the Settings page and time zones."""

import re
from datetime import datetime

import pytest

from app.models import Reminder, User
from app.utils import get_timezone_names
from tests.conftest import TEST_PASSWORD

NEW_PASSWORD = "a-brand-new-password"


def save_profile(client, **overrides):
    data = {"save_profile": "Save changes", "full_name": "Test User",
            "email": "tester@example.com", "timezone": "UTC"}
    data.update(overrides)
    return client.post("/settings", data=data)


def change_password(client, **overrides):
    data = {"change_password": "Change password", "current_password": TEST_PASSWORD,
            "new_password": NEW_PASSWORD, "confirm_new_password": NEW_PASSWORD}
    data.update(overrides)
    return client.post("/settings", data=data)


def get_tester():
    return User.query.filter_by(username="tester").first()


# ---------- Page access ----------

def test_settings_requires_login(client):
    response = client.get("/settings")
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login")


def test_page_shows_saved_values(auth_client):
    html = auth_client.get("/settings").get_data(as_text=True)
    assert 'value="tester@example.com"' in html
    assert re.search(r'<option selected value="UTC">|<option value="UTC" selected>', html)


def test_sidebar_links_to_settings_now_that_it_exists(auth_client):
    html = auth_client.get("/").get_data(as_text=True)
    assert 'href="/settings"' in html
    assert "Day 8" not in html


# ---------- Profile ----------

def test_profile_update_is_saved(auth_client):
    response = save_profile(auth_client, full_name="Kelvin John", email="NEW@Example.com",
                            timezone="Africa/Dar_es_Salaam")
    assert response.status_code == 302
    user = get_tester()
    assert user.full_name == "Kelvin John"
    assert user.email == "new@example.com"
    assert user.timezone == "Africa/Dar_es_Salaam"
    # The header now shows the new name
    assert "Kelvin John" in auth_client.get("/").get_data(as_text=True)


def test_clearing_full_name_falls_back_to_username(auth_client):
    save_profile(auth_client, full_name="Someone")
    save_profile(auth_client, full_name="   ")
    assert get_tester().full_name is None
    assert get_tester().display_name == "tester"


def test_keeping_your_own_email_is_allowed(auth_client):
    assert save_profile(auth_client, email="tester@example.com").status_code == 302


@pytest.mark.parametrize("overrides, message", [
    ({"email": ""}, "Enter your email address."),
    ({"email": "not-an-email"}, "Enter a valid email address."),
    ({"full_name": "x" * 101}, "100 characters or fewer"),
    ({"timezone": "Mars/Olympus_Mons"}, "Not a valid choice"),
])
def test_invalid_profile_is_rejected_and_not_saved(auth_client, overrides, message):
    response = save_profile(auth_client, **overrides)
    assert response.status_code == 200
    assert message in response.get_data(as_text=True)
    assert get_tester().email == "tester@example.com"
    assert get_tester().timezone == "UTC"


def test_email_of_another_user_is_rejected(auth_client, make_user):
    make_user("alice", "alice@example.com")
    response = save_profile(auth_client, email="ALICE@example.com")
    assert "already exists" in response.get_data(as_text=True)
    assert get_tester().email == "tester@example.com"


def test_profile_update_only_changes_the_logged_in_user(auth_client, make_user):
    alice = make_user("alice", "alice@example.com")
    # Extra fields like a user id or username in the form are ignored
    save_profile(auth_client, full_name="Changed", id=alice.id, username="alice")
    assert User.query.filter_by(username="alice").first().full_name is None
    assert get_tester().username == "tester"
    assert get_tester().full_name == "Changed"


def test_html_in_name_is_shown_as_text(auth_client):
    save_profile(auth_client, full_name="<script>alert(1)</script>")
    html = auth_client.get("/settings").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html


# ---------- Change password ----------

def test_password_change_works(auth_client):
    response = change_password(auth_client)
    assert response.status_code == 302
    assert get_tester().check_password(NEW_PASSWORD)
    assert not get_tester().check_password(TEST_PASSWORD)


def test_login_uses_only_the_new_password_afterwards(app, auth_client, login):
    change_password(auth_client)
    assert login(app.test_client(), "tester", TEST_PASSWORD).status_code == 200  # refused
    assert login(app.test_client(), "tester", NEW_PASSWORD).status_code == 302


@pytest.mark.parametrize("overrides, message", [
    ({"current_password": "wrong-password"}, "current password is incorrect"),
    ({"current_password": ""}, "Enter your current password."),
    ({"new_password": "short", "confirm_new_password": "short"}, "8 to 128 characters"),
    ({"confirm_new_password": "something-else"}, "don&#39;t match"),
    ({"new_password": TEST_PASSWORD, "confirm_new_password": TEST_PASSWORD}, "different from your current"),
])
def test_invalid_password_change_is_rejected(auth_client, overrides, message):
    response = change_password(auth_client, **overrides)
    assert response.status_code == 200
    assert message in response.get_data(as_text=True)
    assert get_tester().check_password(TEST_PASSWORD)


def test_password_values_are_never_shown_again(auth_client):
    html = change_password(auth_client, confirm_new_password="mismatch-value").get_data(as_text=True)
    assert NEW_PASSWORD not in html
    assert TEST_PASSWORD not in html


def test_failed_profile_save_does_not_show_errors_on_password_form(auth_client):
    html = save_profile(auth_client, email="bad").get_data(as_text=True)
    assert "Enter a valid email address." in html
    assert "Enter your current password." not in html


def test_failed_password_change_keeps_the_saved_profile_values(auth_client):
    html = change_password(auth_client, current_password="wrong").get_data(as_text=True)
    assert 'value="tester@example.com"' in html
    assert "Enter your email address." not in html


# ---------- CSRF ----------

def test_settings_post_without_csrf_token_is_rejected(app, auth_client):
    app.config["WTF_CSRF_ENABLED"] = True
    assert change_password(auth_client).status_code == 400
    assert get_tester().check_password(TEST_PASSWORD)


def test_settings_post_with_real_csrf_token_works(app, auth_client):
    app.config["WTF_CSRF_ENABLED"] = True
    html = auth_client.get("/settings").get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
    assert save_profile(auth_client, csrf_token=token).status_code == 302


# ---------- Time zones ----------

def test_timezone_list_has_real_places_and_no_aliases():
    names = get_timezone_names()
    assert names[0] == "UTC"
    assert "Africa/Dar_es_Salaam" in names
    assert "Europe/Paris" in names
    assert "US/Eastern" not in names


@pytest.mark.parametrize("timezone, stored, shown", [
    ("UTC", datetime(2099, 1, 15, 12, 0), "Thu 15 Jan 2099, 12:00 UTC"),
    # Summer and winter differ, so daylight saving is handled
    ("Europe/Paris", datetime(2099, 1, 15, 12, 0), "Thu 15 Jan 2099, 13:00 CET"),
    ("Europe/Paris", datetime(2099, 7, 15, 12, 0), "Wed 15 Jul 2099, 14:00 CEST"),
    # Conversion can move the time onto the next day
    ("Africa/Dar_es_Salaam", datetime(2099, 1, 15, 22, 0), "Fri 16 Jan 2099, 01:00 EAT"),
    # An unknown zone in the database falls back to UTC instead of crashing
    ("Not/AZone", datetime(2099, 1, 15, 12, 0), "Thu 15 Jan 2099, 12:00 UTC"),
])
def test_times_are_shown_in_the_users_time_zone(db, auth_client, timezone, stored, shown):
    user = get_tester()
    user.timezone = timezone
    db.session.add(Reminder(user=user, title="Check time", remind_at=stored))
    db.session.commit()
    assert shown in auth_client.get("/").get_data(as_text=True)


def test_changing_time_zone_does_not_change_the_stored_time(db, auth_client):
    stored = datetime(2099, 1, 15, 12, 0)
    db.session.add(Reminder(user=get_tester(), title="Check time", remind_at=stored))
    db.session.commit()
    save_profile(auth_client, timezone="Asia/Tokyo")
    assert Reminder.query.first().remind_at == stored
    assert "Thu 15 Jan 2099, 21:00 JST" in auth_client.get("/").get_data(as_text=True)
