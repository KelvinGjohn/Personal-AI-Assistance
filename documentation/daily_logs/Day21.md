# Development Log — Day 21

| Field | Entry |
|-------|-------|
| Date | 11 November 2026 |
| Day | 21 of 29 |
| Phase | 4 — Advanced features |

## Objectives
- Calendar with a daily and a weekly view of tasks and reminders

## Tasks completed
- `/calendar` with two views: **Week** (Monday to Sunday, the default) and **Day**; "Calendar" in the sidebar is now a working link, so no menu item is left disabled
- A task appears on the day of its due date, a reminder on the day of its time, in time order
- Previous / Today / Next buttons; switching between Day and Week keeps the chosen date
- In the week view each day's heading opens that day; today has a coloured border and a "Today" badge
- Each item links to its edit page; finished tasks and dismissed reminders are struck through; overdue tasks and due reminders show their time in red
- The day view has "New task" and "New reminder" buttons
- Days follow the user's time zone

## How the files connect
`GET /calendar?view=week&date=2026-11-11` → `index()` in `app/routes/calendar.py` → `parse_day()` reads the date → `get_days()` in `app/services/calendar_service.py` runs one query for tasks and one for reminders (both filtered by the user's id) and puts each record on its day → `calendar/index.html`.

## Design decisions
| Decision | Why |
|----------|-----|
| The view and date are in the address (GET) | A day can be bookmarked, refreshed and reached with the Back button |
| Two queries for the whole period, grouped in Python | Simpler and faster than one query per day |
| A day starts at midnight in the user's zone, converted to UTC for the query | 22:00 UTC on Monday is already Tuesday in Tokyo |
| A bad or extreme date shows today instead of an error | The date comes from the address, so anyone can type anything |
| Only years 2000 to 2100, the same as the forms | Extreme dates can't be converted between time zones; Previous/Next disappear at the limit |
| The service returns plain data; the template builds the links | The service can be tested without a web request |
| Days stacked on phones, seven columns only on very wide screens | Seven columns don't fit next to the sidebar on smaller screens |
| No new table | The calendar only shows existing tasks and reminders |

## Files created
- `app/services/calendar_service.py`
- `app/routes/calendar.py`
- `app/templates/calendar/index.html`
- `tests/test_calendar.py`
- `documentation/daily_logs/Day21.md`

## Files modified
- `app/__init__.py`: registers the Blueprint
- `app/static/css/style.css`: calendar styles
- `tests/test_frontend.py`: the "unbuilt pages" test now checks every menu item is a working link
- `PLAN.md`, `README.md`

## Database changes
- None.

## Technologies used
- Python `datetime`, `timedelta` and `zoneinfo`, dataclasses, CSS Grid, Jinja macros, Pytest

## Problems encountered and solutions
1. **Problem:** the page's `today` value would have replaced the `today` the header uses on every page (a date instead of a date and time).
   **Solution:** the calendar passes its own value under a different name, `today_date`.
2. **Problem:** the red "late" colour on the time was overridden by the calendar's own grey.
   **Cause:** two CSS classes of equal strength; the later one wins.
   **Solution:** the template applies either the red class or the grey one, never both.
3. **Problem:** the updated menu test failed for `/chat` with status 302.
   **Cause:** the chat page redirects to a conversation. The test was wrong, not the app.
   **Solution:** the test follows redirects.

## Test results
- `pytest`: **771 passed, 0 failed, 1 warning** (the known Flask-Login warning). 51 are new. They cover reading dates (invalid, impossible and extreme ones), weeks starting on Monday, the year limits, the first and last minute of a day, time zones, a 23-hour day when clocks change, tasks without a due date, done and late items, only the user's own records, both views, the navigation links, HTML in titles shown as text, and login being required.
- Real server with a database **file** (deleted afterwards), two users: the first user's week showed 2 items, today's view 1 item; the second user saw 0 items and nothing of the first user's; extreme and invalid addresses returned a normal page; a visitor was sent to log in.
- Browser at 375×812: week and day views checked with an overdue task with a long title: it wrapped, nothing overflowed, no console errors. At 1500 px wide the week shows seven columns.

## Outstanding issues
- No month view (the plan asks for day and week).
- Tasks without a due date don't appear; they stay on the Tasks page.
- "New task" on a day doesn't pre-fill that date.
- Carried over to Day 24: session cookies identify a user only by id; AI suggestions aren't counted in the message limit.

## Git commit
- `Day 21: Add calendar with day and week views`

## Next day's objectives (Day 22)
- Integration: check all modules work together

## Completion review
Day 21 is **complete**: the calendar shows tasks and reminders by day and by week in the user's time zone, and every page in the menu now exists.
