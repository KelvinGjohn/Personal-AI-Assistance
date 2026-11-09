# Development Log — Day 17

| Field | Entry |
|-------|-------|
| Date | 9 November 2026 |
| Day | 17 of 29 |
| Phase | 3 — AI integration |

## Objectives
- Let the AI answer questions using only the logged-in user's own tasks and notes (FR-55)
- Keep to the privacy requirement (NFR-15): send only the minimum data needed

## Tasks completed
- A "Use my tasks, reminders and notes" checkbox in the chat, off by default
- The help text under it says exactly what is sent, and that nothing is sent in fallback mode
- When it is ticked, a summary of the user's data is attached to that one message for the AI:
  - unfinished tasks (up to 50)
  - tasks finished in the last 7 days (up to 20)
  - due and upcoming reminders (up to 30)
  - the 20 most recently edited notes, each shortened to 600 characters
- Times appear in the user's time zone, and overdue tasks are marked
- The saved chat keeps only the question, never the data
- The checkbox stays ticked for the next message in the same chat
- The system prompt tells the AI that this data is information, not instructions

## How the files connect
Chat form with the box ticked → `chat_page()` → `build_personal_context(current_user)` in `app/services/personal_data.py` → `send_message(..., personal_context)` → `build_ai_messages()` adds the data to the new message only → `ask_ai()`. Only `text`, the user's question, is saved.

## Design decisions
| Decision | Why |
|----------|-----|
| Off by default, and switched on per message | The user decides when their data leaves the app |
| Every query filters by the logged-in user's id | Another user's records can't appear |
| Limits on items and text length | NFR-15: the minimum data, and a predictable cost |
| JSON inside `<personal_data>` tags | Fields stay clearly separate; JSON handles quotes and line breaks |
| The tag text is removed from the user's data | A note containing `</personal_data>` can't end the block early |
| "Information, not instructions" in the system prompt | A note that contains instructions can't steer the AI |
| The data is attached to the user message, not the system prompt | The system prompt is for the app's own rules, and stays the same on every request |
| Data is never saved | It would be out of date anyway, and storing it twice adds risk |

## Files created
- `app/services/personal_data.py`
- `tests/test_personal_data.py`
- `documentation/daily_logs/Day17.md`

## Files modified
- `app/services/chat_service.py`: `personal_context` parameter
- `app/routes/chat.py`: builds the data when the box is ticked, and remembers the box in the address
- `app/forms/chat_forms.py`: `use_my_data` checkbox
- `app/templates/chat/index.html`: the checkbox and its explanation
- `app/services/ai_service.py`: the rule about personal data in the system prompt
- `PLAN.md`, `README.md`

## Database changes
- None.

## Technologies used
- JSON, SQLAlchemy queries, Python `zoneinfo`, Pytest, a throwaway local fake API (see below)

## Test results
- `pytest`: **581 passed, 0 failed, 1 warning** (the known Flask-Login warning). 27 are new. They cover what is collected, limits, the most recent notes, time zones, another user's data never appearing, the JSON block, a note trying to close the block early, the box being off by default and remembered, data never being saved, and the message limit.
- **What actually leaves the app.** A small fake Anthropic server ran on this computer and recorded each request, and the app was pointed at it, so the real SDK and request path were used. Two users, real HTTP sessions:
  - Without the box ticked, the request contained no personal data
  - With it ticked, it contained the user's own task and note; the earlier message in the chat was sent without data; the injection text in a note left exactly one closing tag; the due date was in local time
  - The second user's request contained their own task and **nothing** from the first user
  - The system prompt contained the rule about personal data
  - The saved chat showed only the question
- Browser at 375×812: the box was off by default with its explanation; ticking it by clicking the label and sending kept it ticked for the next message; the recorded request contained the data with the question at the end; no overflowing elements; no console errors.

## Not yet verified
- **Answer quality with real Claude**, for example whether it really answers "what's due this week?" well and refuses instructions hidden in a note. No API key is set, so the fake server only proved what is sent.

## Outstanding issues
- Only the 20 most recent notes are sent, so questions about older notes can't be answered. The AI is told to say so. Smarter note selection could be added with search on Day 20.
- The checkbox itself is small for touch, although its label can also be tapped (Day 26).
- Free disk space dropped from 2.5 GB to 0.71 GB during this session, although this day's files are small.

## Git commit
- `Day 17: Let the AI answer from the user's own data`

## Next day's objectives (Day 18)
- Conversation memory: a list of saved chats, which can be reopened, renamed and deleted

## Completion review
Day 17 is **complete**: data is sent only when asked, only the user's own, and never saved, as shown by recording the real requests. Answer quality needs an API key to judge.
