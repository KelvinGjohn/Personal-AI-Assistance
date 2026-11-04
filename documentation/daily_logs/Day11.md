# Development Log — Day 11

| Field | Entry |
|-------|-------|
| Date | 4 November 2026 |
| Day | 11 of 29 |
| Phase | 2 — Core application development (final day) |

## Objectives
- Create, view, edit and delete notes
- Categories
- Search within notes

## Tasks completed
- `/notes` list: most recently edited first; 20 per page
- Search across title, content and category. Every word must match, in any order, ignoring upper and lower case for English letters
- Category filter, which works together with search
- `/notes/<id>` page shows the whole note and keeps its line breaks
- `/notes/new` and `/notes/<id>/edit` using one form and template
- Delete with a confirmation page
- Category box suggests the user's existing categories
- Dashboard: note titles link to the note, plus a "View all notes" link

## How the files connect
Request → `app/routes/notes.py` → `app/services/note_service.py` queries the `Note` model, always with `user_id` → `NoteForm` in `app/forms/note_forms.py` validates input → `app/templates/notes/` draws the page.

## Design decisions
| Decision | Why |
|----------|-----|
| `autoescape=True` on search | `%` and `_` are SQL wildcards, so "100%" would otherwise match anything starting with "100" |
| Every search word must match | "bank card" narrows the results instead of widening them |
| Search text is limited to 100 characters | Very long searches do no useful work |
| Search uses GET | A search has its own address and survives a refresh |
| Content is shown with `white-space: pre-wrap` | Keeps line breaks while the text stays escaped, so nothing a user types can run as HTML |
| Saving a note goes to the note's own page | The user sees the whole result of what they saved |

## Files created
- `app/services/note_service.py`
- `app/forms/note_forms.py`
- `app/routes/notes.py`
- `app/templates/notes/index.html`, `view.html`, `form.html`, `confirm_delete.html`
- `tests/test_notes.py`
- `documentation/daily_logs/Day11.md`

## Files modified
- `app/services/common.py`: `get_user_categories()` shared by tasks and notes
- `app/services/task_service.py`: uses the shared function
- `app/__init__.py`: registers the Blueprint
- `app/templates/dashboard.html`: links to notes
- `app/static/css/style.css`: `.app-note-content`
- `tests/test_frontend.py`: updated for the new link
- `PLAN.md`, `README.md`

## Database changes
- None. The `notes` table has existed since Day 4.

## Technologies used
- SQLAlchemy `icontains` with `autoescape`, `or_`, Bootstrap forms, Pytest

## Problems encountered and solutions
1. **Problem:** one new test failed on the "no results" message.
   **Cause:** my test expected the quote marks to be escaped, but they are literal text in the template. The search word itself is escaped, and a separate test confirms it.
   **Solution:** corrected the test.
2. **Found by the real-server check:** `CAFÉ` doesn't find `Café`, and `cafe` doesn't either.
   **Cause:** SQLite only ignores upper and lower case for English letters, and it treats accented letters as different letters.
   **Decision:** recorded as a known limit, to be reviewed on Day 20 when global search is built.

## Test results
- `pytest`: **340 passed, 0 failed, 1 warning** (the known Flask-Login warning). 77 are new.
- Real server with a throwaway database (deleted afterwards), two users:
  - `100%` found only "100% done"; `100` found both notes starting with 100
  - SQL text in the search found nothing, and the notes table was unharmed
  - A `<script>` title appeared as plain text
  - The second user, with a valid login and CSRF token, found nothing by searching for the first user's word, and got 404 on view, edit and delete (GET) and edit and delete (POST). The note stayed unchanged
  - POST without a CSRF token → 400; visitor → 302 to login
- Browser at 375×812: typed a real search and pressed Enter (the text stayed in the box and one result appeared), viewed a note with its line breaks, and created a note through the form. No overflowing elements and no console errors.
- Not checked in a browser today: the desktop layout of the notes pages, and the Delete button. It uses the same layout classes as tasks and reminders, and automated tests cover delete.

## Outstanding issues
- Search ignores upper and lower case only for English letters (Day 20).
- On phones, the search box pushes the list down the screen (Day 26).
- Carried over to Day 24: session cookies identify a user only by id.
- Free disk space is 0.91 GB.

## Git commit
- `Day 11: Add notes with categories and search`

## Next day's objectives (Day 12)
- AI service foundation: a configurable AI provider
- A clearly labelled fallback when no API key is set

## Completion review
Day 11 is **complete**, and with it **Phase 2**. Accounts, settings, dashboard, tasks, reminders and notes all work, and each user can only reach their own data.
