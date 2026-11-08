# Development Log — Day 16

| Field | Entry |
|-------|-------|
| Date | 8 November 2026 |
| Day | 16 of 29 |
| Phase | 3 — AI integration |

## Objectives
- Create a reminder from a plain-language request (FR-54)
- Ask for missing details instead of guessing them
- Confirm before saving

## Tasks completed
- "Create with AI" button on the reminder list, opening `/reminders/assist`
- The AI suggests a title, description, date and time
- The suggestion fills in the normal reminder form; only **Save reminder** creates it
- Missing details are asked for:
  - No time: "What time? You said Friday 13 November..."
  - No date, or neither: "When should I remind you? Your request didn't say a date or a time."
  - A time that has already passed: "That time has already passed... When should I remind you instead?"
  In each case the time field is left empty, so the reminder can't be saved until the user chooses
- The AI is told never to make up a time. It may turn only "morning", "afternoon", "evening" and "tonight" into fixed hours, which the user still confirms
- The request page is now shared by tasks and reminders (`assistant/request.html`)

## How the files connect
`POST /reminders/assist` → `assist()` in `app/routes/reminders.py` → `ReminderRequestForm` → `suggest_reminder()` in `app/services/reminder_assistant.py` → `ask_ai_json()` with `REMINDER_SCHEMA` → `clean_suggestion()` checks the values and lists what is missing → `reminders/form.html` shows the question and the form, posting to `/reminders/new`.

## Design decisions
| Decision | Why |
|----------|-----|
| The date and the time are separate fields in the AI's answer | The app can tell exactly which one the request left out |
| A missing or past time leaves the field empty | The reminder can't be saved at a time the user never chose |
| The known date is shown in the question | The user only has to add what is missing |
| Saving goes through the normal create route | Day 10's checks still apply, including "must be in the future" |
| One shared request page | Tasks and reminders differ only in wording |

## Files created
- `app/services/reminder_assistant.py`
- `tests/test_reminder_assistant.py`
- `documentation/daily_logs/Day16.md`

## Files moved
- `app/templates/tasks/assist.html` → `app/templates/assistant/request.html`, made usable for both modules

## Files modified
- `app/forms/reminder_forms.py`: `ReminderRequestForm`
- `app/routes/reminders.py`: `assist()`
- `app/routes/tasks.py`: uses the shared page
- `app/templates/reminders/form.html`: suggestion notice, missing-detail question, optional `form_action`
- `app/templates/reminders/index.html`: "Create with AI" button
- `PLAN.md`, `README.md`

## Database changes
- None.

## Technologies used
- Claude structured outputs, Python `datetime`, Jinja2, Pytest

## Problems encountered and solutions
1. **Problem:** one new test failed on an apostrophe.
   **Cause:** it expected an escaped apostrophe, but the apostrophe is literal text in the template (the same mistake as on Day 11).
   **Solution:** corrected the test.
2. **Problem:** while fixing that, I found one of my own tests only checked something when it wasn't run near midnight.
   **Solution:** rewrote it with a time two days ago, so it always checks.

## Test results
- `pytest`: **554 passed, 0 failed, 1 warning** (the known Flask-Login warning). 47 are new. They cover a complete request, a missing time (with the known date shown), a missing date, both missing, a time already passed, refusal to save without a time, the conversion to UTC on saving, what the AI is told, cleaning bad values, HTML in the AI's answer, the fallback, errors and CSRF.
- Browser at 375×812, fallback mode: typed a request; the confirmation page showed the not-AI notice, the question "When should I remind you?" and an empty time field. Pressing **Save reminder** without a time was refused with "Enter a valid date and time.", keeping the title. After adding a time, the reminder saved and appeared as Upcoming. No overflowing elements and no console errors.

## Not yet verified
- **A real AI suggestion**, including the "What time?" question with a date filled in by the AI. These were tested only with a fake AI, because no API key is set.

## Outstanding issues
- After a refused save, the page heading becomes "New reminder" and the missing-detail question disappears. The field error still says what is needed.
- Reminder suggestions aren't counted in the message limit (Day 24).
- Carried over to Day 24: session cookies identify a user only by id.

## Git commit
- `Day 16: Add AI reminder creation with missing-detail questions`

## Next day's objectives (Day 17)
- AI over personal data: answer questions using only the logged-in user's own tasks and notes (FR-55)

## Completion review
Day 16 is **complete** in fallback mode and in automated tests. A real AI suggestion depends on an API key.
