# Personal AI Assistant

A web-based personal productivity assistant built with Python and Flask. Users can chat with an AI, manage tasks, reminders and notes, and see everything on one dashboard.

> **Status:** Day 12 of 29 — accounts, settings, dashboard, tasks, reminders and notes work, and the AI service is ready for the chat page on Day 13. For sample data, run `python scripts/seed_demo_data.py`, which prints a login for the demo account.

## Planned technology stack

| Component            | Technology                          |
|----------------------|-------------------------------------|
| Language             | Python                              |
| Backend              | Flask                               |
| Frontend             | HTML, CSS, JavaScript, Bootstrap    |
| Database             | SQLite with SQLAlchemy              |
| Authentication       | Flask-Login                         |
| AI integration       | Claude (Anthropic API), configurable, with a labelled non-AI fallback |
| Testing              | Pytest                              |
| Version control      | Git and GitHub                      |

## Documentation

- [Day-by-day plan](PLAN.md)
- [Project proposal](documentation/SRS/Project_Proposal.md)
- [Software Requirements Specification v0.1](documentation/SRS/SRS_v0.1.md)
- [Database design and ER diagram](documentation/Database_Design.md)
- [Daily development logs](documentation/daily_logs/)

## Author

Kelvin John — Computer Science student project.

## Quick start (Windows)

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env      # then give SECRET_KEY a value in .env
python scripts/check_environment.py
python -m pytest
python run.py                    # then open http://127.0.0.1:5000
```

Full instructions: [Development setup](documentation/Development_Setup.md) · Architecture: [System architecture](documentation/UML/System_Architecture.md)

## Turning on real AI (optional)

The app works without an API key: a fallback answers, and it always says it is not AI. For real answers, get an API key from Anthropic and set these in your `.env` file, which Git ignores. Real answers cost money.

```
AI_PROVIDER=claude
AI_API_KEY=your-key-here
```

Then check it works. This sends one short message:

```powershell
python scripts/check_ai.py
```
