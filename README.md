# Personal AI Assistant

A web-based personal productivity assistant built with Python and Flask. Users can chat with an AI, manage tasks, reminders and notes, and see everything on one dashboard.

> **Status:** Day 8 of 29 — users can register, log in, edit their profile, change their password and choose a time zone. For sample data, run `python scripts/seed_demo_data.py`, which prints a login for the demo account.

## Planned technology stack

| Component            | Technology                          |
|----------------------|-------------------------------------|
| Language             | Python                              |
| Backend              | Flask                               |
| Frontend             | HTML, CSS, JavaScript, Bootstrap    |
| Database             | SQLite with SQLAlchemy              |
| Authentication       | Flask-Login                         |
| AI integration       | External AI API (configurable)      |
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
