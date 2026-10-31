# Software Requirements Specification (SRS)
## Personal AI Assistant — version 0.1 (initial)

Structure loosely follows IEEE 830. This is the Day 1 baseline and will be revised as the design matures (Days 2, 4 and 27).

---

## 1. Introduction

### 1.1 Purpose
This document describes what the Personal AI Assistant must do (functional requirements) and how well it must do it (non-functional requirements). It is the reference for design, implementation and testing.

### 1.2 Scope
A Flask web application where a registered user manages tasks, reminders and notes, sees them on a dashboard and calendar, receives in-app notifications, searches everything, and talks to an AI assistant that can answer questions and help create tasks and reminders.

### 1.3 Definitions

| Term | Meaning |
|------|---------|
| User | A registered person using the application |
| Task | A to-do item with title, description, priority, category, due date, status |
| Reminder | A message tied to a specific date and time |
| Note | Free text with a title and category |
| Conversation | A saved sequence of chat messages between the user and the AI |
| AI provider | The external service that generates AI responses |
| Fallback | A labelled non-AI response mode used when no AI provider is configured |
| CRUD | Create, Read, Update, Delete |

### 1.4 Priority scale (MoSCoW)
- **Must**: required for the project to be accepted
- **Should**: important; planned within the 29 days
- **Could**: only if time allows

---

## 2. Overall description

### 2.1 Product perspective
A standalone, server-rendered web application. Three layers:

1. **Presentation**: HTML/Jinja2 templates, Bootstrap, JavaScript (chat).
2. **Application**: Flask routes (Blueprints) and service modules, including `ai_service`.
3. **Data**: SQLite database accessed only through SQLAlchemy models.

The AI provider is an external system reached over HTTPS.

### 2.2 User classes
One user class, the **registered user**. A **visitor** (not logged in) can only see the login and registration pages.

### 2.3 Operating environment
- Server: Python 3.12+, Flask, Windows/Linux
- Client: current Chrome, Edge, Firefox or Safari on desktop, tablet or phone

### 2.4 Constraints
- Must use Python, Flask, SQLite, SQLAlchemy, Flask-Login, Bootstrap and Pytest.
- Secrets (secret key, API keys) only in environment variables, never in source code or Git.
- Must be finished within 29 development days.

### 2.5 Assumptions and dependencies
- An AI provider account and API key are available for the AI features.
- Users have a stable internet connection to use AI features.

---

## 3. Functional requirements

### 3.1 Authentication and account (AUTH)
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | The system shall let a visitor register with username, email and password. | Must |
| FR-02 | The system shall reject registration if the email or username already exists, or the password is shorter than 8 characters. | Must |
| FR-03 | The system shall store passwords only as salted hashes. | Must |
| FR-04 | The system shall let a registered user log in and log out. | Must |
| FR-05 | The system shall redirect a visitor to the login page when they try to open a private page. | Must |
| FR-06 | The system shall let the user update their name and email. | Should |
| FR-07 | The system shall let the user change their password after entering the current one. | Should |
| FR-08 | The system shall let the user set preferences (time zone, theme). | Could |

### 3.2 Dashboard (DASH)
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-10 | The system shall show counts of total, pending, completed and overdue tasks. | Must |
| FR-11 | The system shall show the next upcoming reminders. | Must |
| FR-12 | The system shall show the most recently edited notes. | Should |
| FR-13 | All dashboard figures shall come from the database for the logged-in user. | Must |

### 3.3 Task management (TASK)
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-20 | The user shall be able to create a task with title (required), description, priority (low/medium/high), category and due date. | Must |
| FR-21 | The user shall be able to view, edit and delete their tasks. | Must |
| FR-22 | The user shall be able to mark a task completed or not completed. | Must |
| FR-23 | The user shall be able to filter tasks by status, priority and category. | Should |

### 3.4 Reminder management (REM)
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-30 | The user shall be able to create a reminder with title and date/time. | Must |
| FR-31 | The user shall be able to edit and delete reminders. | Must |
| FR-32 | The system shall list upcoming reminders in time order. | Must |
| FR-33 | The system shall detect reminders whose time has arrived and mark them as due. | Must |

### 3.5 Notes (NOTE)
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-40 | The user shall be able to create, edit and delete notes with title, body and category. | Must |
| FR-41 | The user shall be able to search notes by text. | Must |
| FR-42 | The user shall be able to filter notes by category. | Should |

### 3.6 AI assistant (AI)
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-50 | The user shall be able to send a message and receive an AI response in a chat page. | Must |
| FR-51 | The system shall reject empty messages and show a clear error if the AI provider fails. | Must |
| FR-52 | The system shall show a loading indicator while waiting for a response. | Should |
| FR-53 | The system shall extract a task (title, description, priority, due date) from a plain-language request and show it for confirmation before saving. | Must |
| FR-54 | The system shall extract a reminder (title, date, time) from a plain-language request, ask for missing details, and require confirmation before saving. | Must |
| FR-55 | The AI shall be able to answer questions using only the logged-in user's own tasks and notes. | Should |
| FR-56 | When no AI provider is configured, the system shall use a fallback mode that is clearly labelled as not AI. | Must |

### 3.7 Conversation history (CONV)
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-60 | The system shall save each conversation and its messages. | Must |
| FR-61 | The user shall be able to reopen a past conversation, start a new one, or delete one. | Must |

### 3.8 Notifications (NOTIF)
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-70 | The system shall create an in-app notification when a reminder becomes due or a task's due date arrives. | Must |
| FR-71 | The system shall show an unread count and let the user mark notifications as read. | Must |

### 3.9 Search (SRCH)
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-80 | The user shall be able to search tasks, notes, reminders and conversations from one search box. | Must |
| FR-81 | The user shall be able to filter results by type and sort by date. | Should |

### 3.10 Calendar (CAL)
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-90 | The system shall show reminders and task due dates in a daily and a weekly view. | Must |
| FR-91 | The user shall be able to move to the previous or next day or week. | Must |

---

## 4. Non-functional requirements

| ID | Category | Requirement |
|----|----------|-------------|
| NFR-01 | Security | Passwords are hashed (Werkzeug). Plain-text passwords are never stored or logged. |
| NFR-02 | Security | Every database query for private data is filtered by the current user's ID. A user can never read or change another user's records. |
| NFR-03 | Security | All forms are protected with CSRF tokens. |
| NFR-04 | Security | Secret key and AI API keys are loaded from environment variables. `.env` is listed in `.gitignore`. |
| NFR-05 | Security | All database access goes through SQLAlchemy (parameterized queries) to prevent SQL injection. |
| NFR-06 | Performance | Non-AI pages load in under 1 second locally with up to 1,000 records per user. |
| NFR-07 | Performance | AI requests time out after 30 seconds with a friendly message. |
| NFR-08 | Usability | Main features can be reached within two clicks from the sidebar. |
| NFR-09 | Usability | Layout works at phone (375 px), tablet (768 px) and desktop widths. |
| NFR-10 | Accessibility | Forms have labels, buttons are keyboard-reachable, text contrast is at least 4.5:1. |
| NFR-11 | Reliability | If the AI provider fails, all non-AI features keep working. |
| NFR-12 | Maintainability | Code is organized into Blueprints, models and services, with docstrings on public functions. |
| NFR-13 | Testability | Core modules have automated Pytest tests that run with one command. |
| NFR-14 | Portability | The app runs on Windows and Linux with `pip install -r requirements.txt`. |
| NFR-15 | Privacy | Only data the user enters is stored. Only the minimum user data needed is sent to the AI provider. |

---

## 5. Initial data entities (to be designed on Day 4)

- **User**: id, username, email, password_hash, created_at, preferences
- **Task**: id, user_id, title, description, priority, category, due_date, is_completed, created_at
- **Reminder**: id, user_id, title, remind_at, is_done, created_at
- **Note**: id, user_id, title, body, category, created_at, updated_at
- **Conversation**: id, user_id, title, created_at
- **Message**: id, conversation_id, role (user/assistant), content, created_at
- **Notification**: id, user_id, message, link, is_read, created_at

---

## 6. Traceability to acceptance criteria

| Acceptance criterion | Requirements |
|----------------------|--------------|
| Register and log in | FR-01 to FR-05 |
| Dashboard shows real data | FR-10 to FR-13 |
| Manage tasks | FR-20 to FR-23 |
| Manage reminders | FR-30 to FR-33 |
| Manage notes | FR-40 to FR-42 |
| AI answers questions | FR-50 to FR-52, FR-56 |
| AI-assisted task/reminder creation | FR-53, FR-54 |
| Conversations saved and retrieved | FR-60, FR-61 |
| Notifications | FR-70, FR-71 |
| Search | FR-80, FR-81 |
| Calendar | FR-90, FR-91 |
| User information protected | NFR-01 to NFR-05, NFR-15 |
| Works on desktop and mobile | NFR-09 |
