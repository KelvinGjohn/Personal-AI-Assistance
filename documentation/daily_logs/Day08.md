# Development Log — Day 08

| Field | Entry |
|-------|-------|
| Date | 3 November 2026 |
| Day | 8 of 29 |
| Phase | 2 — Core application development |

## Objectives
- Build the profile page
- Allow users to update their name and email
- Allow users to change their password
- Add basic preferences (time zone)

## Tasks completed
- `/settings` page with two forms: Profile and Change password
- Profile: full name, email and time zone can be edited; the username is shown but cannot be changed
- Change password: requires the current password; the new one must be 8–128 characters, confirmed, and different from the current one
- Times are now shown in the user's own time zone (dashboard lists and header date), including daylight saving
- Settings link in the sidebar (enabled automatically by `navigation.py`) and in the account menu

## How the files connect
`GET/POST /settings` → `index()` in `app/routes/settings.py` → `build_form()` decides which of the two forms reads the submitted data → `ProfileForm` / `ChangePasswordForm` validate → changes are saved on `current_user` → redirect back to the page.

Time display: a time stored in UTC → the `datetime_short` filter → `to_user_time()` in `app/utils.py` → `get_user_timezone()` reads `current_user.timezone`.

## Design decisions
| Decision | Why |
|----------|-----|
| Times stay stored in UTC; only the display is converted | Changing time zone never alters saved data |
| Time zone is a dropdown checked against a fixed list | A made-up zone is rejected by the server |
| An unknown zone in the database falls back to UTC | A bad value can't crash every page |
| Every change is saved on `current_user` | No id comes from the form, so nobody can edit another account |
| Current password required to change the password | Someone using a computer left logged in can't take over the account |
| Redirect after a successful save | Refreshing the page doesn't submit the form twice |

## Files created
- `app/forms/settings_forms.py`
- `app/routes/settings.py`
- `app/templates/settings.html`
- `tests/test_settings.py`
- `documentation/daily_logs/Day08.md`

## Files modified
- `app/utils.py`: `get_timezone_names()`, `get_user_timezone()`, `to_user_time()`; `datetime_short` now converts to the user's zone
- `app/navigation.py`: the header date uses the user's zone
- `app/__init__.py`: registers the settings Blueprint
- `app/templates/base.html`: Settings link in the account menu
- `app/templates/partials/form_field.html`: `control_class` option for dropdowns
- `requirements.txt`: added `tzdata`
- `PLAN.md`, `README.md`

## Database changes
- None. The `full_name` and `timezone` columns have existed since Day 4.

## Technologies used
- Python `zoneinfo`, `tzdata`, WTForms `SelectField`, Flask-Login `current_user`, Pytest

## Problems encountered and solutions
1. **Problem:** Python found 0 time zones on this PC.
   **Cause:** Windows has no time zone database that Python can read.
   **Solution:** installed and pinned the `tzdata` package.
2. **Problem:** with two forms on one page, a mistake in one showed "required" errors in the other.
   **Solution:** `build_form()` lets only the form whose button was pressed read the submitted data. Tests cover both directions.
3. **Problem:** one test "failed" with a context error, although the feature worked.
   **Cause:** pytest ran my helper function `tester()` as a test because its name starts with "test".
   **Solution:** renamed it `get_tester()`.

## Test results
- `pytest`: **117 passed, 0 failed, 1 warning** (the known Flask-Login warning from Day 7). 32 new tests cover: login required, saving, validation, duplicate email, not editing another account, HTML in a name, password rules, passwords never shown again, the two forms staying separate, CSRF, UTC conversion, summer and winter times, a time moving to the next day, an unknown zone, and stored times not changing.
- Browser at 1280×900 on a real server with a throwaway database (deleted afterwards): saved a name and Asia/Tokyo; the header name changed and the date moved from 2 to 3 November (it was 22:39 UTC). Error messages appeared under each password field and the fields were cleared. A real password change succeeded. No console errors.
- Browser at 375×812: no overflowing elements (page width 375 of 375 px). The time zone dropdown has 477 choices.

## Outstanding issues
- After a password change, sessions on other devices stay logged in. To fix in the Day 24 security review.
- Changing the email does not require the current password. To assess on Day 24.
- The 477-item dropdown is long; typing in it jumps to a match. To review on Day 26.
- Dates typed into forms (Days 9–10) must be converted from the user's zone back to UTC.

## Git commit
- `Day 08: Add profile and settings page`

## Next day's objectives (Day 9)
- Task module: create, list, edit, complete and delete tasks
- Priorities, categories, due dates and filters
- Users can only reach their own tasks

## Completion review
Day 8 is **complete**: users can edit their profile, change their password and choose a time zone, and times are displayed in that zone.
