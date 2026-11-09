# Development Log — Day 19

| Field | Entry |
|-------|-------|
| Date | 9 November 2026 |
| Day | 19 of 29 |
| Phase | 4 — Advanced features |

## Objectives
- In-app notifications
- Mark notifications as read

## Tasks completed
- Notifications are created when a reminder's time comes ("Reminder due: ...") and when an unfinished task's due date passes ("Task overdue: ...")
- A bell in the header with the unread count (shown as "99+" above 99)
- `/notifications` lists unread first, then newest, 20 per page; unread ones are bold with a coloured edge
- Opening a notification marks it read and goes to the page it is about
- A tick button marks one as read, and **Mark all as read** marks them all
- "Notifications" in the sidebar is now a working link

## Change of plan from Day 10
The Day 10 log said today would set the reminder's `is_notified` flag when a notification is created. On review, that would have been a mistake. The flag also means "dismissed", so every due reminder would have moved to **Past** as soon as its notification appeared. The Due list, the dashboard warning and Snooze would then never be used.

Instead:
- The reminder is not changed by a notification
- Each notification's link records which reminder or task it is about and for which time (for example `/reminders?status=due&reminder=3&at=202611091739`). A notification with that link is created only once. A snoozed or rescheduled reminder has a new time, so it gets a new notification
- The comment on `Reminder.is_notified` was corrected to match

## How notifications are created
There is no background job. Before each page (GET) a logged-in user opens, `check_for_new_notifications()` runs. It:
1. finds due reminders and overdue tasks from the last 7 days
2. loads, in one query, the links that already have a notification
3. adds at most 20 new ones; any others follow on the next page

## How the files connect
`before_request` in `app/__init__.py` → `check_for_new_notifications()` in `app/services/notification_service.py`. `inject_layout_data()` in `app/navigation.py` → `count_unread()` → the bell in `base.html`. `/notifications` → `app/routes/notifications.py` → `notifications/index.html`.

## Design decisions
| Decision | Why |
|----------|-----|
| Checked when a page opens | No extra process to run or deploy; the check is two small queries |
| Only things due in the last 7 days | Old items aren't news, and they still appear in their own lists |
| At most 20 new at once | A user with many due items doesn't get a slow page |
| Opening a notification is a POST | It changes data (marks it read), so another site can't trigger it with a link |
| Links are checked with `is_safe_redirect()` | Even a link stored in the database can only lead to a page of this app |
| The unread count fails safely | If the database is the problem, the error page still shows |

## Files created
- `app/services/notification_service.py`
- `app/routes/notifications.py`
- `app/templates/notifications/index.html`
- `tests/test_notifications.py`
- `documentation/daily_logs/Day19.md`

## Files modified
- `app/__init__.py`: the check before each page, the Blueprint
- `app/navigation.py`: unread count for the bell, with a safe fallback
- `app/templates/base.html`: the bell
- `app/static/css/style.css`: the badge and unread styling
- `app/models/reminder.py`: corrected comment on `is_notified`
- `tests/test_frontend.py`: updated for the new link
- `PLAN.md`, `README.md`

## Database changes
- None. The `notifications` table has existed since Day 4.

## Technologies used
- Flask `before_request`, SQLAlchemy bulk `update()`, Bootstrap badges, Pytest

## Problems encountered and solutions
1. **Bug found by a test:** with more than 20 due items, the remaining ones would never get a notification.
   **Cause:** each check took the first 20 due items, and every later check took the same 20 again. Those had already been notified, so nothing new was added.
   **Solution:** load the existing links once, skip those, and stop after 20 new ones. This also replaced one query per item with a single query.
2. **Problem:** a test expected a long title to be cut to 255 characters, but titles are limited to 200, so the message could never be that long.
   **Solution:** the test now uses a longer title, as could only come from outside the form. SQLite doesn't enforce lengths, so the cut is still useful.
3. **Problem:** a SQLAlchemy warning in my tests.
   **Cause:** the tests created a notification before looking up the user.
   **Solution:** they now look up the user first. Back to the one known warning.

## Test results
- `pytest`: **668 passed, 0 failed, 1 warning** (the known Flask-Login warning). 46 are new. They cover what creates a notification and what doesn't, no duplicates (including after reading), a new notification after snoozing, the reminder staying Due, the limit of 20 per check, only the user's own records, the bell, a database error in the count, the list order, opening, reading, mark all, another user getting 404, links that change nothing, and CSRF.
- Real server with a throwaway database (deleted afterwards), two users:
  - A due reminder and an overdue task gave the first user 2 notifications; reloading gave no duplicates; the second user had 0
  - The reminder was still in the Due list
  - The second user got 404 trying to open or mark the first user's notification, and 405 using a link
  - Opening a notification went to `/reminders?status=due&reminder=1&at=...` and the count dropped to 1
  - Mark all without a CSRF token → 400
- Browser at 375×812: the bell showed its badge and is 44×44 px; the bell opened the list; unread was bold and listed first; the real **Mark all as read** button cleared the badge; no overflowing elements; no console errors.

## Outstanding issues
- Notifications appear when a page is opened, not by themselves on a page that stays open.
- There is no way to delete notifications; old read ones stay in the list.
- Carried over to Day 24: session cookies identify a user only by id; AI suggestions aren't counted in the message limit.

## Git commit
- `Day 19: Add in-app notifications`

## Next day's objectives (Day 20)
- Global search across tasks, reminders, notes and chats, with filters

## Completion review
Day 19 is **complete**: due reminders and overdue tasks produce notifications once each, users can read and clear them, and the reminder features from Day 10 are unaffected.
