"""
Calendar: the user's tasks and reminders arranged by day.

A task appears on the day of its due date, a reminder on the day of its time.
"A day" means a day in the user's own time zone: times are stored in UTC, so
22:00 UTC on Monday is already Tuesday for a user in Tokyo.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone

from app.forms.task_forms import MAX_YEAR, MIN_YEAR
from app.models import Reminder, Task

VIEWS = ("day", "week")
DEFAULT_VIEW = "week"


@dataclass
class CalendarItem:
    kind: str          # "task" or "reminder"
    id: int
    title: str
    time: datetime     # in the user's time zone
    is_done: bool      # a finished task, or a dismissed reminder
    is_late: bool      # an overdue task, or a reminder still waiting for the user


@dataclass
class CalendarDay:
    date: date
    is_today: bool
    items: list = field(default_factory=list)


def is_allowed_day(day):
    """The same years the task and reminder forms accept."""
    return MIN_YEAR <= day.year <= MAX_YEAR


def parse_day(text, today):
    """Read a date such as "2026-11-11" from the address. Anything else means today."""
    try:
        day = date.fromisoformat(text or "")
    except ValueError:
        return today
    return day if is_allowed_day(day) else today


def week_start(day):
    """The Monday of the week that contains this day."""
    return day - timedelta(days=day.weekday())


def first_day_of_view(view, day):
    return week_start(day) if view == "week" else day


def days_in_view(view):
    return 7 if view == "week" else 1


def move_day(day, number_of_days):
    """The day that many days away, or None if it is outside the allowed years."""
    try:
        moved = day + timedelta(days=number_of_days)
    except OverflowError:
        return None
    return moved if is_allowed_day(moved) else None


def start_of_day_utc(day, tz):
    """Midnight at the start of this day in the user's zone, as a UTC time for queries."""
    local_midnight = datetime.combine(day, time.min, tzinfo=tz)
    return local_midnight.astimezone(timezone.utc).replace(tzinfo=None)


def to_zone(value, tz):
    """A stored UTC time in the given time zone."""
    return value.replace(tzinfo=timezone.utc).astimezone(tz)


def get_days(user_id, first_day, number_of_days, tz, today):
    """
    One CalendarDay for each day, with that day's tasks and reminders in time order.

    Two queries fetch the whole period, then each record is put on its day.
    Both queries start from the user's id, so only their own records appear.
    """
    days = [CalendarDay(date=first_day + timedelta(days=n), is_today=first_day + timedelta(days=n) == today)
            for n in range(number_of_days)]
    by_date = {day.date: day for day in days}

    start = start_of_day_utc(first_day, tz)
    end = start_of_day_utc(first_day + timedelta(days=number_of_days), tz)

    tasks = Task.query.filter(Task.user_id == user_id,
                              Task.due_date >= start, Task.due_date < end).all()
    reminders = Reminder.query.filter(Reminder.user_id == user_id,
                                      Reminder.remind_at >= start, Reminder.remind_at < end).all()

    items = [CalendarItem("task", task.id, task.title, to_zone(task.due_date, tz),
                          is_done=task.is_completed, is_late=task.is_overdue)
             for task in tasks]
    items += [CalendarItem("reminder", reminder.id, reminder.title, to_zone(reminder.remind_at, tz),
                           is_done=reminder.status == "past", is_late=reminder.status == "due")
              for reminder in reminders]

    for item in sorted(items, key=lambda item: (item.time, item.kind, item.title.casefold(), item.id)):
        day = by_date.get(item.time.date())
        if day is not None:
            day.items.append(item)
    return days


def count_items(days):
    return sum(len(day.items) for day in days)
