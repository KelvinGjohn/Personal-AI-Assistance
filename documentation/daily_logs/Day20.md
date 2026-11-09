# Development Log — Day 20

| Field | Entry |
|-------|-------|
| Date | 9 November 2026 |
| Day | 20 of 29 |
| Phase | 4 — Advanced features |

## Objectives
- Global search across tasks, reminders, notes and chats
- Filters
- Review the accent limit found on Day 11

## Tasks completed
- `/search` with one search box and an **In** filter (Everything, Tasks, Reminders, Notes, Chats); "Search" in the sidebar is now a working link
- Every word must match somewhere in the record:
  - tasks: title, description, category
  - reminders: title, description
  - notes: title, content, category
  - chats: title and every message
- "Everything" shows up to 5 results per type, with **Show all N** links; one type shows up to 50
- Each result links to its record, with a short excerpt where the match was found, the match highlighted
- Upper and lower case and accents are now ignored everywhere, including the notes search from Day 11

## Fixing the Day 11 limit
SQLite's `LIKE` only ignores case for English letters, so `CAFÉ` didn't find `Café`. The fix:
- `fold()` in `app/text_search.py` lower-cases with `casefold()`, splits letters from their accents (Unicode NFKD) and drops the accents: `Café` → `cafe`, `Straße` → `strasse`
- It is registered as a SQL function on every SQLite connection (in `app/extensions.py`), so queries can use `fold(column)`
- Matching uses `instr(fold(column), word) > 0` instead of `LIKE`, so `%` and `_` are ordinary characters without escaping

## How the files connect
`GET /search?q=...&type=...` → `index()` in `app/routes/search.py` → `search()` in `app/services/search_service.py` → one query per type, each starting from the user's id, using `all_words_match()` from `app/text_search.py` → `find_snippet()` for the excerpts → `search/index.html`.

## Design decisions
| Decision | Why |
|----------|-----|
| A SQL function for folding | Keeps searching inside the database, with the same rules for every module |
| `instr` instead of `LIKE` | No wildcard characters to escape |
| Chats match through an `EXISTS` subquery | Each chat appears once, however many messages match |
| Excerpts are split into before / match / after | Jinja escapes each part; only the `<mark>` around the match is HTML |
| Search uses GET | A search has its own address and survives a refresh |
| At most 10 words and 100 characters | Very long searches do no useful work |

## Files created
- `app/text_search.py`
- `app/services/search_service.py`
- `app/routes/search.py`
- `app/templates/search/index.html`
- `tests/test_search.py`
- `documentation/daily_logs/Day20.md`

## Files modified
- `app/extensions.py`: registers `fold()` on each SQLite connection
- `app/services/note_service.py`: uses the shared matching
- `app/__init__.py`: registers the Blueprint
- `tests/test_frontend.py`: updated for the new link
- `PLAN.md`, `README.md`

## Database changes
- None. `fold()` is added to each connection when it opens; nothing is stored.

## Technologies used
- SQLite user-defined functions (`create_function`), Python `unicodedata`, SQLAlchemy `func`, `and_`, `or_` and `any()`, Pytest

## Problems encountered and solutions
1. **Problem:** 22 new tests failed with "Unable to build URLs outside an active request".
   **Cause:** the tests called `search()` directly, and it builds links with `url_for()`, which needs a request.
   **Solution:** a fixture gives each search test a request context, as a real page has.
2. **Problem:** a SQLAlchemy warning in one test.
   **Cause:** the same ordering mistake as on Day 19: a note was created before looking up the user.
   **Solution:** the test looks up the user first.

## Test results
- `pytest`: **720 passed, 0 failed, 1 warning** (the known Flask-Login warning). 52 are new. They cover folding (accents, `ß`, `%` and `_`), the Day 11 notes limit, each field of each type, every word having to match, chats matching across messages but appearing once, the type filter, only the user's own records, preview and full limits, excerpts (including `ß`, which becomes two letters), escaping, SQL text and time zones. All 77 earlier notes tests still pass with the new matching.
- Real server with a database **file** (deleted afterwards), two users: `CAFE`, `café`, `ecole` and `STRASSE` each found the note; `bank` found 3 results, 1 in notes only; the notes page found `ECOLE`; the second user found 0 results and nothing of the first user's; SQL text found nothing and harmed nothing; a visitor was sent to log in.
- Browser at 375×812: typed `BANK` and pressed Enter: the results were grouped with counts, the matches highlighted, no overflowing elements, no console errors.

## Outstanding issues
- A match in a title isn't highlighted; only excerpts from longer text are.
- Every record is checked in Python, which suits one person's data. A very large database would need a full-text index (SQLite FTS5).
- Carried over to Day 24: session cookies identify a user only by id; AI suggestions aren't counted in the message limit.

## Git commit
- `Day 20: Add global search ignoring case and accents`

## Next day's objectives (Day 21)
- Calendar: daily and weekly views of tasks and reminders

## Completion review
Day 20 is **complete**: one search covers every module, finds text regardless of case and accents, and fixes the limit recorded on Day 11.
