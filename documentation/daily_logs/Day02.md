# Development Log — Day 02

| Field | Entry |
|-------|-------|
| Date | 1 November 2026 |
| Day | 2 of 29 |
| Phase | 1 — Planning and project foundation |

## Objectives
- Explain the complete application architecture
- Explain how frontend, backend and database communicate
- Set up the development environment (Python, venv, VS Code)
- Initialize Git and GitHub

## Tasks completed
- Documented the three-tier / MVC architecture with Mermaid diagrams (`documentation/UML/System_Architecture.md`)
- Created a Python 3.14 virtual environment and installed all planned libraries
- Pinned the library versions in `requirements.txt`
- Created `.env.example` (no secrets) for configuration
- Wrote a Windows setup guide including VS Code extensions
- Wrote `scripts/check_environment.py` and `tests/test_environment.py` to verify the setup

## Files created
- `requirements.txt`
- `.env.example`
- `scripts/check_environment.py`
- `tests/test_environment.py`
- `documentation/UML/System_Architecture.md`
- `documentation/Development_Setup.md`
- `documentation/daily_logs/Day02.md`

## Files modified
- `PLAN.md` (Day 2 status)
- `README.md` (quick start)

## Technologies used
- Python 3.14, venv, pip, Pytest, Mermaid, Git

## Problems encountered and solutions
- **Problem:** `test_flask_can_talk_to_sqlite` failed with
  `DLL load failed while importing _collections_cy: The filename or extension is too long.`
  **Cause:** the project was in a very deep temporary folder. SQLAlchemy's compiled module inside `venv` exceeded Windows' 260-character path limit.
  **Solution:** moved the project to the short path `C:\Users\user\Desktop\JOHN\Personal_AI_Assistant` and recreated the virtual environment there.

## Test results
- First run (long path): 2 passed, 1 failed (the path problem above).
- After the move: `check_environment.py` printed `[OK]` for Python 3.14.0, all 9 packages and the Flask + SQLAlchemy + SQLite connection.
- `pytest -v`: **3 passed, 0 failed** (`test_python_version_is_supported`, `test_all_required_packages_installed`, `test_flask_can_talk_to_sqlite`).

## Outstanding issues
- None.

## Git commit
- `Day 02: Configure development environment`

## Next day's objectives (Day 3)
- Create the full folder structure and the Flask application factory
- Add configuration classes that read `.env`
- Add the entry point `run.py` and the first route
- Run the first version of the application

## Completion review
Day 2 is **complete**: the architecture is documented with diagrams, the virtual environment is installed from `requirements.txt`, and all environment tests pass. Days 1–2 are pushed to GitHub.
