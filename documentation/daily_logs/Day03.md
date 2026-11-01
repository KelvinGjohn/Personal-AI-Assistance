# Development Log — Day 03

| Field | Entry |
|-------|-------|
| Date | 1 November 2026 |
| Day | 3 of 29 |
| Phase | 1 — Planning and project foundation |

## Objectives
- Create the complete folder structure
- Initialize the Flask application (application factory)
- Configure application settings and environment variables
- Create the application entry point
- Establish routing
- Run the first version of the application

## Tasks completed
- Created the planned folders (`app/routes`, `app/models`, `app/services`, `app/templates`, `app/static`, `config`, `database`, `documentation/testing`, `documentation/final_report`). Empty folders hold a `.gitkeep` so Git tracks them.
- `config/settings.py`: `Config` base class plus `DevelopmentConfig`, `TestingConfig`, `ProductionConfig`; secrets come from environment variables.
- `app/__init__.py`: `create_app()` loads `.env`, chooses a config, refuses to start without `SECRET_KEY`, registers Blueprints.
- `app/routes/main.py`: `main` Blueprint with `/` (home page) and `/health` (JSON status).
- `app/templates/index.html` + `app/static/css/style.css`: first page.
- `run.py`: entry point.
- `tests/conftest.py` (shared `app` and `client` fixtures) and `tests/test_app.py` (6 tests).
- Local `.env` created from `.env.example` with a random 64-character `SECRET_KEY` (ignored by Git).

## How the files connect
`run.py` → calls `create_app()` in `app/__init__.py` → `load_dotenv()` reads `.env` → `config/settings.py` reads those variables → the chosen config class is loaded into `app.config` → `register_blueprints()` imports `app/routes/main.py` → a request to `/` runs `index()` → `render_template("index.html")` builds the HTML from `app/templates/` and links `app/static/css/style.css`.

## Files created
- `run.py`
- `config/__init__.py`, `config/settings.py`
- `app/__init__.py`, `app/routes/__init__.py`, `app/routes/main.py`
- `app/templates/index.html`, `app/static/css/style.css`
- `tests/conftest.py`, `tests/test_app.py`
- `.gitkeep` files in the empty planned folders
- `documentation/daily_logs/Day03.md`

## Files modified
- `PLAN.md` (Day 3 status), `README.md` (how to run)

## Technologies used
- Flask (application factory, Blueprints, Jinja2, `url_for`, `jsonify`), python-dotenv, Pytest

## Problems encountered and solutions
- No errors today. Design choice: the app raises a clear `RuntimeError` when `SECRET_KEY` is missing instead of silently using an insecure default (supports NFR-04).

## Test results
- `pytest -v`: **9 passed, 0 failed** (6 new app tests + 3 environment tests).
- Manual run with `python run.py`:
  - `GET /health` → `200`, `{"app": "Personal AI Assistant", "status": "ok"}`
  - `GET /` → `200`, page heading "Personal AI Assistant"
  - `GET /static/css/style.css` → `200`

## Outstanding issues
- None.

## Git commit
- `Day 03: Implement Flask application structure`

## Next day's objectives (Day 4)
- Identify the database entities and draw the ER diagram (Mermaid)
- Create SQLAlchemy models: User, Task, Reminder, Note, Conversation, Message, Notification
- Set up relationships and test database creation

## Completion review
Day 3 is **complete**: the Flask app starts, serves the home page and health check, reads its settings from `.env`, and all tests pass.
