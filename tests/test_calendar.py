"""Day 21 - tests for the calendar's day and week views."""

import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from app.models import Reminder, Task, User
from app.services.calendar_service import (
    get_days,
    move_day,
    parse_day,
    start_of_day_utc,
    week_start,
)

UTC = ZoneInfo("UTC")
TODAY = date(2026, 11, 11)  # a Wednesday


def get_tester():
    return User.query.filter_by(username="tester").first()


def add(db, *records):
    db.session.add_all(records)
    db.session.commit()


def page(client, path):
    return client.get(path).get_data(as_text=True)


def titles(day):
    return [item.title for item in day.items]


# ---------- Dates ----------

@pytest.mark.parametrize("text, expected", [
    ("2026-12-25", date(2026, 12, 25)),
    ("2000-01-01", date(2000, 1, 1)),
    ("2100-12-31", date(2100, 12, 31)),
    ("1999-12-31", TODAY),     # before the allowed years
    ("2101-01-01", TODAY),     # after the allowed years
    ("0001-01-01", TODAY),
    ("9999-12-31", TODAY),
    ("2026-02-30", TODAY),     # not a real date
    ("25/12/2026", TODAY),
    ("tomorrow", TODAY),
    ("", TODAY),
    (None, TODAY),
    ("<script>", TODAY),
])
def test_parse_day(text, expected):
    assert parse_day(text, TODAY) == expected


@pytest.mark.parametrize("day, monday", [
    (date(2026, 11, 9), date(2026, 11, 9)),    # Monday
    (date(2026, 11, 11), date(2026, 11, 9)),   # Wednesday
    (date(2026, 11, 15), date(2026, 11, 9)),   # Sunday
    (date(2027, 1, 1), date(2026, 12, 28)),    # the week crosses a year
])
def test_week_starts_on_monday(day, monday):
    assert week_start(day) == monday


def test_move_day_stops_at_the_allowed_years():
    assert move_day(date(2026, 11, 11), 7) == date(2026, 11, 18)
    assert move_day(date(2026, 11, 11), -1) == date(2026, 11, 10)
    assert move_day(date(2100, 12, 31), 1) is None
    assert move_day(date(2000, 1, 1), -1) is None


def test_start_of_day_follows_the_time_zone():
    day = date(2026, 11, 11)
    assert start_of_day_utc(day, UTC) == datetime(2026, 11, 11, 0, 0)
    assert start_of_day_utc(day, ZoneInfo("Asia/Tokyo")) == datetime(2026, 11, 10, 15, 0)
    assert start_of_day_utc(day, ZoneInfo("America/New_York")) == datetime(2026, 11, 11, 5, 0)


# ---------- What appears on each day ----------

def test_tasks_and_reminders_appear_on_their_day_in_time_order(db, auth_client):
    user = get_tester()
    add(db,
        Task(user=user, title="Evening task", due_date=datetime(2099, 3, 10, 18, 0)),
        Reminder(user=user, title="Morning reminder", remind_at=datetime(2099, 3, 10, 8, 30)),
        Task(user=user, title="Noon task", due_date=datetime(2099, 3, 10, 12, 0)),
        Task(user=user, title="Next day", due_date=datetime(2099, 3, 11, 9, 0)))
    days = get_days(user.id, date(2099, 3, 10), 2, UTC, TODAY)
    assert titles(days[0]) == ["Morning reminder", "Noon task", "Evening task"]
    assert [item.kind for item in days[0].items] == ["reminder", "task", "task"]
    assert titles(days[1]) == ["Next day"]


def test_first_and_last_minute_of_a_day_belong_to_it(db, auth_client):
    user = get_tester()
    add(db,
        Task(user=user, title="Just before", due_date=datetime(2099, 3, 9, 23, 59)),
        Task(user=user, title="Midnight", due_date=datetime(2099, 3, 10, 0, 0)),
        Task(user=user, title="Last minute", due_date=datetime(2099, 3, 10, 23, 59)),
        Task(user=user, title="Just after", due_date=datetime(2099, 3, 11, 0, 0)))
    days = get_days(user.id, date(2099, 3, 10), 1, UTC, TODAY)
    assert titles(days[0]) == ["Midnight", "Last minute"]


def test_tasks_without_a_due_date_are_not_on_the_calendar(db, auth_client):
    user = get_tester()
    add(db, Task(user=user, title="Someday"))
    days = get_days(user.id, date(2099, 3, 9), 7, UTC, TODAY)
    assert all(day.items == [] for day in days)


def test_days_follow_the_users_time_zone(db, auth_client):
    user = get_tester()
    # 22:00 UTC on the 10th is 07:00 on the 11th in Tokyo
    add(db, Reminder(user=user, title="Late call", remind_at=datetime(2099, 3, 10, 22, 0)))
    tokyo = ZoneInfo("Asia/Tokyo")
    assert titles(get_days(user.id, date(2099, 3, 10), 1, tokyo, TODAY)[0]) == []
    day = get_days(user.id, date(2099, 3, 11), 1, tokyo, TODAY)[0]
    assert titles(day) == ["Late call"]
    assert day.items[0].time.strftime("%H:%M") == "07:00"


def test_day_with_a_clock_change_is_still_complete(db, auth_client):
    user = get_tester()
    paris = ZoneInfo("Europe/Paris")
    # 29 March 2026: clocks go forward in Paris, so the day has 23 hours
    add(db,
        Task(user=user, title="Start", due_date=datetime(2026, 3, 28, 23, 0)),   # 00:00 local
        Task(user=user, title="End", due_date=datetime(2026, 3, 29, 21, 59)),    # 23:59 local
        Task(user=user, title="Next", due_date=datetime(2026, 3, 29, 22, 0)))    # 00:00 next day
    days = get_days(user.id, date(2026, 3, 29), 2, paris, TODAY)
    assert titles(days[0]) == ["Start", "End"]
    assert titles(days[1]) == ["Next"]


def test_done_and_late_items_are_marked(db, auth_client):
    user = get_tester()
    add(db,
        Task(user=user, title="Late task", due_date=datetime(2001, 5, 5, 9, 0)),
        Task(user=user, title="Done task", due_date=datetime(2001, 5, 5, 10, 0), is_completed=True),
        Reminder(user=user, title="Due reminder", remind_at=datetime(2001, 5, 5, 11, 0)),
        Reminder(user=user, title="Dismissed", remind_at=datetime(2001, 5, 5, 12, 0), is_notified=True),
        Task(user=user, title="Future task", due_date=datetime(2099, 5, 5, 9, 0)))
    past = {item.title: item for item in get_days(user.id, date(2001, 5, 5), 1, UTC, TODAY)[0].items}
    assert (past["Late task"].is_late, past["Late task"].is_done) == (True, False)
    assert (past["Done task"].is_late, past["Done task"].is_done) == (False, True)
    assert (past["Due reminder"].is_late, past["Due reminder"].is_done) == (True, False)
    assert (past["Dismissed"].is_late, past["Dismissed"].is_done) == (False, True)
    future = get_days(user.id, date(2099, 5, 5), 1, UTC, TODAY)[0].items[0]
    assert (future.is_late, future.is_done) == (False, False)


def test_today_is_marked(db, auth_client):
    days = get_days(get_tester().id, week_start(TODAY), 7, UTC, TODAY)
    assert [day.is_today for day in days] == [False, False, True, False, False, False, False]


def test_another_users_items_never_appear(db, auth_client, make_user):
    alice = make_user("alice")
    add(db,
        Task(user=alice, title="ALICE task", due_date=datetime(2099, 3, 10, 9, 0)),
        Reminder(user=alice, title="ALICE reminder", remind_at=datetime(2099, 3, 10, 10, 0)))
    days = get_days(get_tester().id, date(2099, 3, 9), 7, UTC, TODAY)
    assert all(day.items == [] for day in days)
    assert "ALICE" not in page(auth_client, "/calendar?view=week&date=2099-03-10")
    assert "ALICE" not in page(auth_client, "/calendar?view=day&date=2099-03-10")


# ---------- The page ----------

@pytest.mark.parametrize("path", ["/calendar", "/calendar?view=day&date=2099-03-10"])
def test_login_required(client, path):
    response = client.get(path)
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login")


def test_week_is_the_default_view_and_shows_seven_days(auth_client):
    html = page(auth_client, "/calendar?date=2099-03-11")
    assert html.count('aria-labelledby="day-') == 7
    for day in range(9, 16):
        assert f'id="day-2099-03-{day:02d}"' in html
    assert "09 Mar to 15 Mar 2099" in html
    assert "0 items" in html


def test_day_view_shows_one_day(db, auth_client):
    user = get_tester()
    add(db,
        Task(user=user, title="Hand in essay", due_date=datetime(2099, 3, 10, 14, 30)),
        Task(user=user, title="Other day", due_date=datetime(2099, 3, 11, 9, 0)))
    html = page(auth_client, "/calendar?view=day&date=2099-03-10")
    assert "Tuesday, 10 March 2099" in html
    assert "Hand in essay" in html and "14:30" in html
    assert "Other day" not in html
    assert "1 item ·" in html


def test_empty_day_says_so(auth_client):
    assert "Nothing scheduled for this day." in page(auth_client, "/calendar?view=day&date=2099-03-10")


def test_items_link_to_their_edit_pages(db, auth_client):
    user = get_tester()
    task = Task(user=user, title="A task", due_date=datetime(2099, 3, 10, 9, 0))
    reminder = Reminder(user=user, title="A reminder", remind_at=datetime(2099, 3, 10, 10, 0))
    add(db, task, reminder)
    html = page(auth_client, "/calendar?view=week&date=2099-03-10")
    assert f'href="/tasks/{task.id}/edit"' in html
    assert f'href="/reminders/{reminder.id}/edit"' in html


def test_previous_next_and_today_links(auth_client):
    week = page(auth_client, "/calendar?view=week&date=2099-03-11")
    assert 'href="/calendar?view=week&amp;date=2099-03-02"' in week
    assert 'href="/calendar?view=week&amp;date=2099-03-16"' in week
    assert 'href="/calendar?view=week"' in week
    day = page(auth_client, "/calendar?view=day&date=2099-03-11")
    assert 'href="/calendar?view=day&amp;date=2099-03-10"' in day
    assert 'href="/calendar?view=day&amp;date=2099-03-12"' in day


def test_switching_view_keeps_the_date(auth_client):
    html = page(auth_client, "/calendar?view=week&date=2099-03-11")
    assert 'href="/calendar?view=day&amp;date=2099-03-11"' in html


def test_no_link_past_the_allowed_years(auth_client):
    html = page(auth_client, "/calendar?view=day&date=2100-12-31")
    assert 'aria-label="Next day"' not in html
    assert 'aria-label="Previous day"' in html
    html = page(auth_client, "/calendar?view=day&date=2000-01-01")
    assert 'aria-label="Previous day"' not in html
    assert 'aria-label="Next day"' in html


@pytest.mark.parametrize("query", [
    "view=month", "view=%3Cscript%3E", "date=nonsense", "date=9999-12-31", "date=0001-01-01",
    "date=2026-02-30", "view=day&date=" + "9" * 500, "date=2000-01-01", "date=2100-12-31",
    "view=week&date=2000-01-01", "view=week&date=2100-12-31",
])
def test_bad_or_extreme_addresses_still_show_a_page(auth_client, query):
    assert auth_client.get("/calendar?" + query).status_code == 200


def test_titles_are_shown_as_text(db, auth_client):
    bad = "<img src=x onerror=alert(1)>"
    add(db, Task(user=get_tester(), title=bad, due_date=datetime(2099, 3, 10, 9, 0)))
    html = page(auth_client, "/calendar?view=day&date=2099-03-10")
    assert bad not in html
    assert "&lt;img" in html


def test_page_uses_the_users_time_zone(db, auth_client):
    user = get_tester()
    user.timezone = "Asia/Tokyo"
    add(db, Reminder(user=user, title="Late call", remind_at=datetime(2099, 3, 10, 22, 0)))
    assert "Late call" not in page(auth_client, "/calendar?view=day&date=2099-03-10")
    html = page(auth_client, "/calendar?view=day&date=2099-03-11")
    assert "Late call" in html and "07:00" in html


def test_done_task_is_struck_through_and_late_time_is_red(db, auth_client):
    user = get_tester()
    add(db,
        Task(user=user, title="Finished", due_date=datetime(2001, 5, 5, 9, 0), is_completed=True),
        Task(user=user, title="Forgotten", due_date=datetime(2001, 5, 5, 10, 0)))
    html = page(auth_client, "/calendar?view=day&date=2001-05-05")
    assert re.search(r'app-item-done"\s+href="[^"]+">Finished<', html)
    assert re.search(r'app-text-overdue">10:00<', html)
    assert not re.search(r'app-text-overdue">09:00<', html)


def test_menu_links_to_calendar(auth_client):
    assert re.search(r'nav-link active"\s+href="/calendar"', page(auth_client, "/calendar"))
