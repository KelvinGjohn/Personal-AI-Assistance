# Development Log — Day 22

| Field | Entry |
|-------|-------|
| Date | 12 November 2026 |
| Day | 22 of 29 |
| Phase | 4 — Advanced features |

## Objectives
- Make sure all modules work together
- Close the gaps between modules found while checking

## Tasks completed
- **Integration tests** (`tests/test_integration.py`): they follow a user through the whole app using only the real pages and forms, starting from registration
- **Dashboard connected to the other pages:**
  - each summary card opens its page (Tasks, Reminders, Notes, chat history)
  - task and reminder titles open their edit pages (before, only notes were links)
  - a new line shows how many items are on today's calendar and opens today's day view
- **Calendar connected to the forms:** "New task" and "New reminder" in the day view open the form with that day filled in at 09:00 (the limit recorded on Day 21)

## What the integration tests check
| Journey | What must be true |
|---------|-------------------|
| Create one of each record | It appears on the dashboard, in search, on the calendar and on its own page |
| Time passes | The due reminder and overdue task create notifications; opening one leads back to the record; the bell empties |
| Finish, reopen, edit, delete | The dashboard, calendar and search all change to match |
| Change the time zone | The dashboard, reminders, search and calendar all show the new time, and the calendar moves the item to the right day |
| Two users | The second user sees nothing of the first on any page, and gets "not found" for every address of the first user's records |
| Log out | Every page asks for a login; logging back in shows the same data |
| Delete a user | All of their data goes, and nobody else's |

## How the files connect
- Dashboard: `index()` in `app/routes/main.py` passes the user's time zone to `get_dashboard_data()`, which calls `count_items_today()` in `app/services/calendar_service.py`: the same code the calendar page uses, so the two can't disagree.
- Calendar to forms: the day view links to `/tasks/new?date=2026-11-12` → `new()` in `app/routes/tasks.py` calls `starting_time()` → the form opens with `2026-11-12 09:00`. Reminders work the same way.

## Design decisions
| Decision | Why |
|----------|-----|
| Integration tests use only pages and forms | They test what a real user does, including the parts between modules |
| "Time passing" is done by moving a saved time into the past | The forms rightly refuse reminders in the past |
| The dashboard reuses the calendar's counting | One rule for what "today" contains |
| The date for a new form comes from the address and is checked | Anyone can type anything there; a bad date is ignored and the form opens empty |
| The pre-filled date is only a starting value | The user can change it, and the form's normal checks still run when saving |

## Files created
- `tests/test_integration.py`
- `documentation/daily_logs/Day22.md`

## Files modified
- `app/services/calendar_service.py`: `starting_time()` and `count_items_today()`
- `app/services/dashboard_service.py`: card links, today's count
- `app/routes/main.py`, `app/routes/tasks.py`, `app/routes/reminders.py`
- `app/templates/dashboard.html`, `app/templates/calendar/index.html`
- `app/static/css/style.css`: a card that is a link
- `PLAN.md`, `README.md`

## Database changes
- None.

## Technologies used
- Flask test client with several separate "browsers", Pytest parametrize, regular expressions for reading pages

## Problems encountered and solutions
1. **Problem:** the two-user test failed on the search page.
   **Cause:** the page repeats the word that was searched for, so the second user's own search word was on the page. The test was wrong, not the app.
   **Solution:** for the search page the test checks "0 results" instead.

No faults were found in the app itself: every journey worked the first time. The gaps were missing links between pages, which are now added.

## Test results
- `pytest`: **796 passed, 0 failed, 1 warning** (the known Flask-Login warning). 25 are new.
- Real server with a database **file** (deleted afterwards), two users: forms opened from the calendar were pre-filled; the first user's dashboard showed 1 of each record with working links, search found 4 results and the calendar showed 2 items in time order; the second user got "not found" for the first user's task and saw nothing; finishing the task changed the dashboard and calendar; deleting it removed it from search and the calendar; after logging out every page asked for a login.
- Browser at 375×812: the dashboard with the new calendar line and linked cards fits, nothing overflowed, no console errors.

## Outstanding issues
- After saving a task opened from the calendar, the app goes to the task list, not back to the calendar.
- Notes and chats have no dates on the calendar (by design: they have no due time).
- Not yet verified: a real answer from Claude (no API key is set), so the AI parts were tested with the fallback only.
- Carried over to Day 24: session cookies identify a user only by id; AI suggestions aren't counted in the message limit.

## Git commit
- `Day 22: Connect dashboard and calendar to other pages, add integration tests`

## Next day's objectives (Day 23)
- Functional testing and a test report

## Completion review
Day 22 is **complete**: the modules are linked to each other and tests prove that a change in one place shows up everywhere it should. This also finishes Phase 4.
