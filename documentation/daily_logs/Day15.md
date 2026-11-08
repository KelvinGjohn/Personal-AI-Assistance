# Development Log — Day 15

| Field | Entry |
|-------|-------|
| Date | 8 November 2026 |
| Day | 15 of 29 |
| Phase | 3 — AI integration |

## Objectives
- Create a task from a plain-language request (FR-53)
- Show the extracted task for confirmation before saving

## Tasks completed
- "Create with AI" button on the task list, opening `/tasks/assist`
- The user describes the task, and the AI suggests a title, description, priority, category and due date
- The suggestion fills in the normal task form. The user can change anything, and only **Save task** creates the task
- The AI is told today's date and the user's time zone, so words like "Friday" and "tomorrow" work
- The AI is given the user's own categories (only theirs), so it can reuse one
- Fallback mode: the request becomes the title, and a notice says clearly that nothing was worked out by AI
- `ask_ai_json()` in the AI service, for answers in a fixed format (Claude structured outputs)

## How the files connect
`POST /tasks/assist` → `assist()` in `app/routes/tasks.py` → `TaskRequestForm` validates → `suggest_task()` in `app/services/task_assistant.py` → `ask_ai_json()` → `ClaudeProvider.ask_json()` with a JSON schema → `clean_suggestion()` checks every value → `TaskForm(formdata=None, data=...)` → `tasks/form.html` with `action="/tasks/new"` → the normal create route saves it.

## Design decisions
| Decision | Why |
|----------|-----|
| The suggestion only fills in the form; the normal create route saves it | Confirmation is built in (FR-53), and all of Day 9's validation and ownership checks still apply |
| Structured output with a JSON schema | Claude's reply must have exactly these fields, so it never has to be guessed from free text |
| Every value from the AI is checked again | A bad date, an unknown priority or an over-long title becomes a safe default, never an error |
| Dates are worked out in the user's time zone | Saving converts them to UTC exactly as for a typed date |
| Low effort for extraction, medium for chat | Pulling fields out of one sentence doesn't need deep thinking, and costs less |
| The fallback doesn't pretend to extract anything | FR-56: it must never pass as AI |

## Files created
- `app/services/task_assistant.py`
- `app/templates/tasks/assist.html`
- `tests/test_task_assistant.py`
- `documentation/daily_logs/Day15.md`

## Files modified
- `app/services/claude_provider.py`: `ask_json()`; shared `_send()` and `_read_text()`
- `app/services/ai_service.py`: `ask_ai_json()`, `check_messages()`
- `app/forms/task_forms.py`: `TaskRequestForm`
- `app/routes/tasks.py`: `assist()`
- `app/templates/tasks/form.html`: suggestion notice, optional `form_action`
- `app/templates/tasks/index.html`: "Create with AI" button
- `app/static/css/style.css`: outline buttons in the app's colour
- `PLAN.md`, `README.md`

## Database changes
- None.

## Technologies used
- Claude structured outputs (`output_config.format` with `json_schema`), JSON, WTForms, Pytest

## Problems encountered and solutions
1. **Problem:** the disk was full (22 MB free) at the start of the day.
   **Solution:** stopped before writing anything. The developer freed space (2.17 GB at the end of the day).
2. **Problem:** a new test caused a SQLAlchemy warning.
   **Cause:** my test created a task before the second user, in the wrong order.
   **Solution:** reordered the test; back to the one known warning.

## Test results
- `pytest`: **507 passed, 0 failed, 1 warning** (the known Flask-Login warning). 36 are new. They cover nothing being saved before confirmation, the form posting to the normal create route, the time zone, the schema, what the AI is told (only the user's own categories), cleaning bad values, HTML in the AI's answer, the fallback, errors, CSRF, and the Claude request with the real SDK and a fake network layer.
- Browser at 375×812, fallback mode: typed a request; the confirmation page showed the not-AI notice, the request in the title, and a form posting to `/tasks/new`; nothing was saved yet. After changing the title and priority and pressing the real **Save task** button, the task appeared with High priority. No overflowing elements and no console errors.

## Not yet verified
- **A real AI suggestion.** No API key is set, so the AI was replaced by a fake one in tests, and the Claude request was tested with a fake network layer.

## Outstanding issues
- Task suggestions are not counted in the message limit from Day 14 (Day 24 security review).
- The two buttons above the task list are 38 px tall, below the 44 px goal (Day 26).
- Carried over to Day 24: session cookies identify a user only by id.

## Git commit
- `Day 15: Add AI task creation with confirmation`

## Next day's objectives (Day 16)
- AI reminder assistance: create a reminder from plain language, ask for missing details, and confirm before saving (FR-54)

## Completion review
Day 15 is **complete** in fallback mode and in automated tests. A real AI suggestion depends on an API key.
