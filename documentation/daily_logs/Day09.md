# Development Log — Day 09

| Field | Entry |
|-------|-------|
| Date | 3 November 2026 |
| Day | 9 of 29 |
| Phase | 2 — Core application development |

## Objectives
- Create, list, edit, complete and delete tasks
- Priorities, categories and due dates
- Filters
- Users can only reach their own tasks

## Tasks completed
- `/tasks` list: unfinished first, then earliest due date, with undated tasks after dated ones; 20 per page
- Filters for status (pending, overdue, completed), priority and category, which can be combined
- `/tasks/new` and `/tasks/<id>/edit` using one form and template
- Complete and reopen buttons that return to the same filtered list
- Delete with a confirmation page
- Due dates are typed in the user's time zone and saved in UTC
- Category box suggests the user's existing categories
- "View all tasks" link on the dashboard; the Tasks menu item stays highlighted on all task pages

## How the files connect
Request → `app/routes/tasks.py` → `get_user_task_or_404()` and the other functions in `app/services/task_service.py` query the `Task` model, always with `user_id` → `TaskForm` in `app/forms/task_forms.py` validates input → `app/templates/tasks/` draws the page.

## Design decisions
| Decision | Why |
|----------|-----|
| Another user's task returns 404, not 403 | Nobody can find out which task ids exist |
| Owner is set from `current_user`, never from the form | A forged form can't create or move tasks for someone else |
| Separate complete and reopen routes, not one toggle | Double clicks or an old tab can't flip the state back |
| Complete, reopen and delete only change data on POST | A link or image on another site can't trigger them |
| Filters use GET | A filtered list has its own address and survives a refresh |
| Dates limited to years 2000–2100 | Extreme dates crash time zone conversion |
| Data logic is in a service | The AI features on Day 15 can reuse it |

## Files created
- `app/services/task_service.py`
- `app/forms/task_forms.py`
- `app/routes/tasks.py`
- `app/templates/tasks/index.html`, `form.html`, `confirm_delete.html`
- `tests/test_tasks.py`
- `documentation/daily_logs/Day09.md`

## Files modified
- `app/utils.py`: `user_time_to_utc()`, `utc_to_user_input()`; `is_safe_redirect()` moved here from `routes/auth.py` so both Blueprints can use it
- `app/routes/auth.py`: imports `is_safe_redirect` from `utils`
- `app/models/task.py`: `is_overdue` property
- `app/__init__.py`: registers the tasks Blueprint
- `app/navigation.py`: the menu item is highlighted for its whole Blueprint
- `app/templates/dashboard.html`: "View all tasks" link
- `app/templates/partials/form_field.html`: `help_text` option
- `app/static/css/style.css`: task list and icon buttons
- `requirements.txt`: pinned `WTForms`, since the code now imports `SelectChoice` from it
- `tests/conftest.py`: see problems 1 and 2
- `tests/test_auth.py`, `tests/test_frontend.py`: updated for the moved helper and the new link
- `PLAN.md`, `README.md`

## Database changes
- None. The `tasks` table has existed since Day 4.

## Technologies used
- SQLAlchemy filtering, ordering and pagination, WTForms `DateTimeLocalField`, HTML `datalist`, Pytest

## Problems encountered and solutions
1. **Problem:** four new tests reported that saved changes were missing.
   **Cause:** the test's database session kept old copies of records. The same flaw meant a check that something "did not change" could pass without really looking at the database.
   **Solution:** `RealisticClient` now clears the test session's cached records after every request, so all tests read the real database. All earlier tests still pass with this stricter setup.
2. **Problem:** the test suite took about 3 minutes.
   **Cause:** password hashing is slow on purpose, and most tests logged in.
   **Solution:** tests reuse one hash, and `auth_client` writes the login directly into the session. `test_auth.py` still tests real hashing and the real login page. The suite now takes 40–60 seconds.
3. **Problem:** a very large task id or page number could crash the page.
   **Cause:** SQLite can't accept numbers above 2^63 − 1.
   **Solution:** such ids return 404 and page numbers are corrected. Both have tests.
4. **Problem:** the list said "1 task match your filters".
   **Found by:** the browser check.
   **Solution:** fixed the wording and added a test.
5. **Problem:** the browser logged straight in as a test user from an old session cookie.
   **Cause:** the session stores only the user id, and the recreated test database reused that id. See "Outstanding issues".

## Test results
- `pytest`: **184 passed, 0 failed, 1 warning** (the known Flask-Login warning). 67 are new.
- Real server with a throwaway database (deleted afterwards), two users:
  - 09:00 entered in Tokyo was stored as 00:00 UTC and displayed as 09:00 JST
  - The second user, with a valid login and CSRF token, got 404 on GET edit and delete, and POST edit, complete, reopen and delete. The task stayed unchanged
  - POST without a CSRF token → 400; visitor → 302 to login; huge id → 404; huge page → 200
- Browser at 1280×900: validation error, creating an overdue task with a long title, completing a task, combined filters, the delete confirmation and the real Delete button. No console errors.
- Browser at 375×812: no overflowing elements, and icon buttons measured 44×44 px.

## Outstanding issues
- For the Day 24 security review: session cookies identify a user only by id. If an id is ever reused, an old cookie would log in as the new owner. This is also why other devices stay logged in after a password change (Day 8). One fix should solve both.
- On phones, the filters push the task list down the screen, and long titles wrap into a narrow column. To review on Day 26.
- After editing or deleting a task, the list returns without its filters. Only complete and reopen keep them.

## Git commit
- `Day 09: Add task management module`

## Next day's objectives (Day 10)
- Reminder management: create, list, edit and delete
- Detect reminders that are due

## Completion review
Day 9 is **complete**: users can manage their own tasks through the full cycle, with filters and time zones working, and another user's tasks can't be reached.
