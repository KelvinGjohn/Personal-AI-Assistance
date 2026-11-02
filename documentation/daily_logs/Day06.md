# Development Log — Day 06

| Field | Entry |
|-------|-------|
| Date | 2 November 2026 |
| Day | 6 of 29 |
| Phase | 2 — Core application development |

## Objectives
- Create the main dashboard
- Display task statistics, upcoming reminders and recent notes
- Create productivity summary cards
- Connect dashboard information to backend data

## Tasks completed
- `app/services/dashboard_service.py`: functions that read the statistics and lists from the database, always filtered by `user_id`
- `dashboard.html`: four summary cards, "Tasks due soon" (with priority and overdue labels), "Upcoming reminders", "Productivity" (progress bar) and "Recent notes", each with an empty state
- `datetime_short` template filter, which labels times as UTC
- `scripts/seed_demo_data.py`: creates a `demo` user with sample data that cannot be logged into

## How the files connect
`GET /` → `index()` in `app/routes/main.py` picks the user → `get_dashboard_data(user.id)` in `dashboard_service.py` queries the models → the results go to `render_template("dashboard.html", ...)` → the page is drawn inside `base.html`.

## Design decision: temporary user selection
The roadmap builds the dashboard (Day 6) before login (Day 7), so there is no logged-in user yet. `get_dashboard_user()` temporarily returns the first user in the database, and the page shows a "Development view" notice saying so. **This page is not private until Day 7.** The service already takes a `user_id`, so only the route needs to change.

## Files created
- `app/services/dashboard_service.py`
- `scripts/seed_demo_data.py`
- `tests/test_dashboard.py`
- `documentation/daily_logs/Day06.md`

## Files modified
- `app/routes/main.py`: the dashboard uses real data (the fixed card list was removed)
- `app/templates/dashboard.html`: panels connected to data (replaces Day 5's empty panels)
- `app/utils.py`: added `datetime_short`
- `app/__init__.py`: registers the filter
- `app/static/css/style.css`: priority badges, overdue text, progress bar
- `PLAN.md`, `README.md`

## Files removed
- `app/services/.gitkeep`: the folder now holds real code

## Database changes
- No table changes. The demo data is only in the local `instance/assistant.db`, which is not in Git.

## Technologies used
- SQLAlchemy queries (`filter_by`, `filter`, `order_by`, `limit`, `count`), Jinja2 conditionals and filters, Bootstrap list groups and progress bar, Pytest

## Problems encountered and solutions
- **Phone screenshot looked cut off on the right.** Measuring the page showed no element past the screen edge (page width 375 of 375 px; first card at 16–359 px), so it was a screenshot capture problem, not a layout bug. No code change was needed.

## Test results
- `pytest`: **42 passed, 0 failed** (14 new dashboard tests + 28 earlier tests). New tests cover: zero tasks (no division by zero), status counts, completed tasks never counted as overdue, the 7-day window, sorting, the 5-item limit, another user's data excluded, the empty page, HTML in a note title being escaped, and running the seed script twice.
- Browser check at 1280×900 with demo data. Values matched a hand calculation from the seed data: 8 tasks, 3 completed, 5 pending, 1 overdue, 38% complete, 2 completed in the last 7 days, 3 upcoming reminders (the past one excluded), 3 notes, 1 conversation.
- Browser check at 375×812: no sideways scrolling and no overflowing elements (measured). A clean screenshot of the lower panels at this width could not be captured.

## Outstanding issues
- The dashboard shows the first user to anyone until Day 7.
- Times are shown in UTC until Day 8.
- Items can't be created in the app yet (Days 9–11), so the only data today is demo data.

## Git commit
- `Day 06: Connect dashboard to database`

## Next day's objectives (Day 7)
- Registration and login forms with input validation
- Password hashing and Flask-Login
- Logout and protected routes
- Dashboard uses the logged-in user; the temporary code and notice are removed

## Completion review
Day 6 is **complete**: the dashboard displays real database information, correct for the sample data, with empty states when there is none. Privacy depends on Day 7.
