# Development Log — Day 05

| Field | Entry |
|-------|-------|
| Date | 2 November 2026 |
| Day | 5 of 29 |
| Phase | 2 — Core application development |

## Objectives
- Create the main HTML structure
- Design the navigation sidebar and application header
- Establish the main dashboard layout
- Implement responsive CSS
- Introduce Bootstrap components

## Tasks completed
- `base.html`: shared layout that every page extends (Bootstrap 5.3.3, Bootstrap Icons, sidebar, header, footer, skip link)
- `partials/sidebar.html`: sidebar that is fixed on large screens and a slide-in menu on small screens (Bootstrap `offcanvas-lg`)
- `partials/flash_messages.html`: shows `flash()` messages as Bootstrap alerts
- `app/navigation.py`: the menu is defined as data; pages not built yet appear disabled with a "Day N" badge instead of a broken link
- `dashboard.html`: summary cards and empty panels using the Bootstrap grid (the numbers arrive on Day 6)
- `errors/404.html`, `errors/500.html`: friendly error pages that use the normal layout
- `style.css`: rewritten with the theme colours as CSS variables and a small-screen layout

## How the files connect
A route calls `render_template("dashboard.html", ...)` → `dashboard.html` says `{% extends "base.html" %}` and fills its `title`, `page_title` and `content` blocks → `base.html` includes the sidebar and flash partials → the context processor `inject_layout_data()` (registered in `create_app()`) gives every template `nav_items`, `app_name` and `today`.

## Files created
- `app/navigation.py`
- `app/templates/base.html`, `dashboard.html`
- `app/templates/partials/sidebar.html`, `partials/flash_messages.html`
- `app/templates/errors/404.html`, `errors/500.html`
- `tests/test_frontend.py`
- `documentation/daily_logs/Day05.md`

## Files modified
- `app/__init__.py`: added `register_template_helpers()` and `register_error_handlers()`
- `app/routes/main.py`: `/` now renders the dashboard
- `app/static/css/style.css`: replaced the Day 3 styles (reason: the new layout needs them)
- `tests/test_app.py`: home page test updated for the dashboard
- `PLAN.md`, `README.md`

## Files removed
- `app/templates/index.html`: replaced by `dashboard.html`

## Database changes
- None.

## Technologies used
- Bootstrap 5.3.3, Bootstrap Icons 1.11.3, Jinja2 template inheritance, CSS variables, Pytest

## Problems encountered and solutions
1. **Problem:** saving files failed with `ENOSPC: no space left on device`.
   **Cause:** the C: drive had 0 bytes free. No existing project files were damaged.
   **Solution:** the developer removed three duplicate installers from Downloads, freeing 2.47 GB, and the failed files were written again.
2. **Problem:** the browser check showed a pale desktop sidebar with hard-to-read items and no app name. All automated tests still passed.
   **Cause:** on large screens Bootstrap's `offcanvas-lg` sets a transparent background with `!important` and hides the offcanvas header.
   **Solution:** overrode both in `style.css`. Lesson: HTML tests cannot detect visual bugs, so pages must also be checked in a browser.

## Test results
- `pytest`: **28 passed, 0 failed** (9 new layout tests + 19 earlier tests).
- Browser check at 1280×800 (after the fix): dark sidebar with app name, four cards in one row, two panels side by side.
- Browser check at 375×812: cards stack in one column, no sideways scrolling (page width 375 of 375 px), menu button opens the sidebar and the close button closes it, 404 page displays correctly.
- Bootstrap's script loaded with its integrity hash; the only console error was the 404 requested on purpose.
- Not checked today: tablet width (planned for Day 26).

## Outstanding issues
- The summary cards show a dash until Day 6 connects real data.
- The header shows "Guest" until login is built on Day 7.
- The Bootstrap Icons link has no integrity hash yet (to review in the Day 24 security check).

## Git commit
- `Day 05: Build initial frontend`

## Next day's objectives (Day 6)
- Show real task statistics, upcoming reminders and recent notes on the dashboard
- Add productivity summary cards connected to backend data

## Completion review
Day 5 is **complete**: the layout, sidebar, header and dashboard page work on desktop and phone widths, and the tests pass. Dashboard data is Day 6's objective.
