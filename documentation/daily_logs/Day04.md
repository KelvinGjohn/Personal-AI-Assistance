# Development Log — Day 04

| Field | Entry |
|-------|-------|
| Date | 1 November 2026 |
| Day | 4 of 29 |
| Phase | 1 — Planning and project foundation |

## Objectives
- Identify database entities and design the ER diagram
- Create SQLAlchemy models for users, tasks, reminders, notes and conversations
- Establish relationships between entities
- Configure SQLAlchemy and test database connectivity

## Tasks completed
- Designed 7 tables: `users`, `tasks`, `reminders`, `notes`, `conversations`, `messages`, `notifications`
- `app/extensions.py`: shared `db = SQLAlchemy()` object; SQLite foreign keys switched on for every connection
- `app/utils.py`: `utc_now()` so all times are stored in UTC
- One model file per entity in `app/models/`, with relationships, cascades, indexes and CHECK constraints
- `create_app()` now calls `init_database()`, which connects SQLAlchemy and runs `db.create_all()`
- `/health` now also checks the database (`"database": "ok"`; returns HTTP 503 if the database fails)
- Test fixtures: each test gets a fresh in-memory database; `make_user` helper
- ER diagram (Mermaid) and data dictionary in `documentation/Database_Design.md`

## Files created
- `app/extensions.py`, `app/utils.py`
- `app/models/__init__.py`, `user.py`, `task.py`, `reminder.py`, `note.py`, `conversation.py`, `notification.py`
- `tests/test_models.py`
- `documentation/Database_Design.md`, `documentation/daily_logs/Day04.md`

## Files modified
- `app/__init__.py`: added `init_database()`
- `app/routes/main.py`: `/health` checks the database
- `tests/conftest.py`: app context, `db` and `make_user` fixtures
- `tests/test_app.py`: health test expects the `database` field
- `PLAN.md`, `README.md`

## Database changes
- New file database `instance/assistant.db` (ignored by Git), created automatically on start
- 7 tables, 6 foreign keys, 2 CHECK constraints, 2 UNIQUE constraints

## Technologies used
- Flask-SQLAlchemy 3.1, SQLAlchemy 2.1, SQLite, Pytest, Mermaid

## Problems encountered and solutions
- **Problem:** when the server was started for the manual check, requests to `http://127.0.0.1:5000/health` hung.
  **Cause:** another `python run.py` (started at 12:55 from a separate PowerShell window, using a global Python 3.15 rather than the project's venv) was already using port 5000. On Windows two servers can share a port, and requests then go unpredictably to one of them.
  **Solution:** stopped only the test server and re-ran the check on port 5001 without the auto-reloader. The other server was left running. Lesson: only run one development server at a time, and start it from the activated venv.

## Test results
- `pytest`: **19 passed, 0 failed** (10 new model tests + 9 earlier tests). New tests cover: all tables created, defaults, unique username/email, task–user relationship, invalid priority rejected, foreign key enforcement, ordered conversation messages, invalid message role rejected, deleting a user deletes all their data, users only see their own tasks.
- Manual check (port 5001): `GET /health` → `200 {"app": "Personal AI Assistant", "database": "ok", "status": "ok"}`; `GET /` → `200`.
- `instance/assistant.db` inspected with `sqlite3`: all 7 tables present with the expected foreign keys.

## Outstanding issues
- None.

## Git commit
- `Day 04: Create database models`

## Next day's objectives (Day 5)
- Base template with Bootstrap 5
- Navigation sidebar and header
- Main dashboard layout, responsive CSS

## Completion review
Day 4 is **complete**: the database is designed, documented, created automatically, and verified by 10 automated tests and a manual inspection.
