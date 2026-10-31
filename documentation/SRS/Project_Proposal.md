# Project Proposal — Personal AI Assistant

| | |
|---|---|
| Author | Kelvin John |
| Version | 0.1 (Day 1) |
| Date | 31 October 2026 |
| Duration | 29 development days |

## 1. Introduction and purpose

The Personal AI Assistant is a full-stack web application that combines everyday productivity tools (tasks, reminders, notes and a calendar) with a conversational AI. Instead of switching between several apps, the user works from one dashboard and can create or find information by clicking or by asking in plain language.

The project is also a learning exercise. It covers requirements engineering, architecture, database design, authentication, API integration, testing, security and deployment.

## 2. Problem statement

Students and professionals keep their commitments spread across separate to-do apps, calendars, note apps and chatbots. This leads to:

- missed deadlines, because reminders are kept apart from tasks;
- time lost searching several places for one piece of information;
- AI chatbots that know nothing about the user's own tasks and notes;
- repetitive manual typing for every new task or reminder.

## 3. Objectives

**General objective:** design, build, test, document and deploy a secure web-based personal assistant that brings daily productivity into one place and supports it with AI, within 29 days.

**Specific objectives:**

1. **OBJ-1:** Secure registration and login with hashed passwords, where each user sees only their own data.
2. **OBJ-2:** Create, read, update and delete tasks, reminders and notes, saved in SQLite.
3. **OBJ-3:** Use an external AI API for chat, questions and answers, and creating tasks and reminders from plain language (the user confirms before anything is saved).
4. **OBJ-4:** A responsive dashboard, calendar, global search and in-app notifications.
5. **OBJ-5:** Check the system with automated Pytest tests plus functional and security test reports.
6. **OBJ-6:** Deploy to a public host, with complete technical documentation and a user manual.

## 4. Target users

| User group | Typical needs |
|------------|---------------|
| University students | Track assignments and exams, keep lecture notes, ask study questions |
| Working professionals | Plan the work day, get meeting reminders, capture tasks quickly |
| Freelancers and individuals | Organize personal and client commitments, search everything in one place |

Assumption: users can use a web browser; no technical knowledge is needed. Each account belongs to one person (no shared workspaces).

## 5. Scope

### In scope
- User accounts: register, login, logout, profile and settings
- Dashboard with live statistics from the database
- Tasks with priority, category, due date and completion status
- Reminders with date and time, and detection of due reminders
- Notes with categories and search
- AI chat, question answering and saved conversations
- AI-assisted creation of tasks and reminders, with confirmation
- AI answers about the user's own notes and tasks
- In-app notifications, global search, daily and weekly calendar
- Automated tests, security review, deployment and documentation

### Out of scope
- Native mobile apps (the web app will be responsive instead)
- Email, SMS or push notifications outside the app
- Voice input and speech output
- Sync with Google Calendar, Outlook or other services
- Team collaboration and shared lists
- Training or hosting our own AI model
- Payments or subscriptions

## 6. Limitations and assumptions

- The quality and cost of AI answers depend on the external provider.
- SQLite suits one server and modest traffic, which is enough for this project.
- Notifications appear only while the app is open in the browser.
- When no AI API key is set, a clearly labelled development fallback is used so other modules can still be tested. It is not presented as real AI.

## 7. Feasibility analysis

| Type | Verdict | Reasoning |
|------|---------|-----------|
| Technical | Feasible | The stack is mature and well documented. Flask and SQLAlchemy are beginner-friendly, and the AI is reached through a simple HTTPS API. |
| Economic | Feasible | All tools are free and open source. The only cost is AI API usage, kept low with short prompts and limits. Free hosting tiers are available. |
| Operational | Feasible | Runs in any modern browser, and the familiar dashboard layout needs little training. AI actions always require user confirmation. |
| Schedule | Tight but feasible | Possible only with strict daily scope: one module per day, tested before moving on. Days 22–25 act as buffer for integration and fixes. |

### Main risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| AI API unavailable or out of credit | AI features cannot be demonstrated | Provider-agnostic service plus labelled fallback |
| A day takes longer than planned | Schedule slips | Fix the day before moving on; use buffer days 22–25 |
| Security mistakes (exposed keys, other users' data visible) | Data leak | `.env` excluded from Git, every query filtered by the current user, Day 24 security review |
| Losing work | Lost progress | Daily commits pushed to GitHub |

## 8. Technology selection

| Layer | Technology | Reason |
|-------|-----------|--------|
| Language | Python | Readable, with a strong ecosystem for AI and web |
| Backend | Flask with Blueprints | Small core, so each added piece is understood |
| Frontend | Jinja2 templates, Bootstrap 5, JavaScript | Server-rendered pages, responsive grid built in, JavaScript only where needed (chat) |
| Database | SQLite with SQLAlchemy | No server setup; the ORM maps tables to classes and protects against SQL injection |
| Authentication | Flask-Login, Flask-WTF | Session handling, route protection, CSRF tokens on forms |
| AI | Provider-agnostic service module | Provider and key are set in `.env`, so the provider can be changed |
| Testing | Pytest | Automated regression tests |
| Version control | Git and GitHub | A daily commit history shows progress |
