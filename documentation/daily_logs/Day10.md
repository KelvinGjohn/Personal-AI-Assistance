# Development Log — Day 10

| Field | Entry |
|-------|-------|
| Date | 4 November 2026 |
| Day | 10 of 29 |
| Phase | 2 — Core application development |

## Objectives
- Create, list, edit and delete reminders
- Detect reminders that are due

## Tasks completed
- `/reminders` list: due first, then upcoming, then past; 20 per page
- Filter pills: All, Due (with a count), Upcoming, Past
- `/reminders/new` and `/reminders/<id>/edit` using one form and template
- Due detection: `Reminder.status` for one reminder, `count_due_reminders()` for a user
- **Dismiss** (moves a due reminder to Past) and **Snooze 1 hour**
- Dashboard warning, "You have N reminders due", with a link to the due list
- Delete with a confirmation page
- Times are typed in the user's time zone and saved in UTC

## How the files connect
Request → `app/routes/reminders.py` → `app/services/reminder_service.py` queries the `Reminder` model, always with `user_id` → `ReminderForm` in `app/forms/reminder_forms.py` validates input → `app/templates/reminders/` draws the page. The dashboard calls `count_due_reminders()` through `dashboard_service.py`.

## Design decisions
| Decision | Why |
|----------|-----|
| Three states: upcoming, due, past | Without a "past" state, a due reminder could never stop being due |
| Dismiss uses the existing `is_notified` column | A new column would break existing databases, because `create_all()` can't alter tables. Day 19 sets the same flag when it creates a notification, so the meaning stays the same: the user has been told |
| A new time makes a dismissed reminder go off again | Moving a reminder means the user wants to be reminded at the new time |
| A new reminder must be in the future, but an old one can still be edited | Fixing a typo in an old reminder's title shouldn't be refused |
| Dismiss and snooze only act on a due reminder | An old open tab can't hide or move an upcoming reminder |
| Shared `app/services/common.py`, `partials/pagination.html` and `redirect_back()` | Tasks and reminders need identical logic, and notes will too |

## Files created
- `app/services/common.py`: `get_owned_or_404()`, `paginate_query()`
- `app/services/reminder_service.py`
- `app/forms/reminder_forms.py`
- `app/routes/reminders.py`
- `app/templates/reminders/index.html`, `form.html`, `confirm_delete.html`
- `app/templates/partials/pagination.html`
- `tests/test_reminders.py`
- `documentation/daily_logs/Day10.md`

## Files modified
- `app/models/reminder.py`: `status` property; updated comment on `is_notified`
- `app/services/task_service.py`, `app/routes/tasks.py`: now use the shared helpers
- `app/forms/task_forms.py`: `check_year_range()` so both forms share it
- `app/utils.py`: `whole_minute()`, `redirect_back()`
- `app/services/dashboard_service.py`: due count; a reminder at exactly the current time now counts as due, not upcoming
- `app/templates/dashboard.html`: due warning, "View all reminders" link
- `app/templates/tasks/index.html`: shared pagination, renamed CSS classes
- `app/static/css/style.css`: status badges and pills; `app-task*` renamed `app-item*`
- `app/__init__.py`: registers the Blueprint
- `scripts/seed_demo_data.py`: the old reminder now demonstrates a due reminder
- `tests/test_tasks.py`, `tests/test_frontend.py`: updated for the shared code and the new link
- `PLAN.md`, `README.md`

## Database changes
- No table changes. `is_notified` now also means "dismissed".

## Technologies used
- SQLAlchemy `case` ordering, Jinja2 macros, Bootstrap nav pills, Pytest

## Problems encountered and solutions
1. **Problem:** my first time zone test for "must be in the future" would have passed even if the zone were ignored.
   **Solution:** rewrote it with a clock time that is in the past in Tokyo but would look like the future if read as UTC.
2. **Problem:** saving an old reminder's form could have made a dismissed reminder go off again.
   **Cause:** forms only hold whole minutes, so a stored time with seconds would look changed.
   **Solution:** times are compared at whole minutes. A test covers this.
3. **Problem:** desktop screenshots came out shrunken in the browser pane.
   **Solution:** checked that view with page measurements and a small image. Dismiss and Snooze were pressed as real buttons.

## Test results
- `pytest`: **263 passed, 0 failed, 1 warning** (the known Flask-Login warning). 79 are new.
- Real server with a throwaway database (deleted afterwards), two users:
  - A past time was refused; 09:00 in Tokyo was stored as 00:00 UTC
  - The dashboard warned only the owner about their 3 due reminders
  - The second user, with a valid login and CSRF token, got 404 on GET edit and delete, and POST edit, dismiss, snooze and delete. The reminder stayed unchanged
  - POST without a CSRF token → 400; visitor → 302 to login; huge id → 404
- Browser at 1280×900: Dismiss moved a reminder to Past; Snooze moved one to Upcoming, 1 hour ahead; the due count updated from 3 to 1 on the pill and the dashboard warning; no sideways scrolling.
- Browser at 375×812: no overflowing elements; Dismiss and the pills measured 44 px tall. No console errors.
- Not tested in a browser today: the reminder form (covered by automated tests, and the same pattern as the task form checked on Day 9).

## Outstanding issues
- Due reminders are detected when a page loads, so an open page doesn't update by itself, and the warning appears only on the dashboard. Day 19 adds notifications across the app.
- Carried over to Day 24: session cookies identify a user only by id.
- Free disk space is down to 0.93 GB.

## Git commit
- `Day 10: Add reminder management`

## Next day's objectives (Day 11)
- Notes: create, list, edit and delete
- Categories and search within notes

## Completion review
Day 10 is **complete**: users can manage their own reminders, and due reminders are detected and shown on the list and the dashboard. Phase 2 finishes with notes on Day 11.
