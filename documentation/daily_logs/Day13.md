# Development Log — Day 13

| Field | Entry |
|-------|-------|
| Date | 5 November 2026 |
| Day | 13 of 29 |
| Phase | 3 — AI integration |

## Objectives
- Build a working chat page
- Connect it to the AI service from Day 12
- Label fallback answers clearly

## Tasks completed
- `/chat` opens the most recent chat, or a new one if there are none
- `/chat/new` starts a chat, and `/chat/<id>` shows and continues one
- Messages are saved as conversations, with the title taken from the first message
- Fallback mode: a notice at the top of the page, and each fallback reply has a dashed border and a "Not AI" badge
- Loading indicator: "Thinking..." with the Send button disabled (FR-52)
- Enter sends and Shift+Enter starts a new line
- If the AI fails, the error is shown, nothing is saved, and the text stays in the box (FR-51)

## How the files connect
`POST /chat/<id>` → `chat_page()` in `app/routes/chat.py` → `ChatForm` validates → `send_message()` in `app/services/chat_service.py` → `build_ai_messages()` → `ask_ai()` → the question and answer are saved → redirect back to the chat → `app/templates/chat/index.html`, with `app/static/js/chat.js` for the indicator and keyboard.

## Design decisions
| Decision | Why |
|----------|-----|
| A normal form that works without JavaScript | Simple and dependable; the script only adds comfort |
| Save only after the AI answers | A failure leaves no half-finished conversation |
| Redirect after sending | Refreshing the page can't send the message twice |
| Fallback replies are never sent to the AI as history | They aren't real answers, so the AI shouldn't treat them as things it said |
| Only the current chat's recent messages are sent (at most 20, plus the new one) | Privacy (NFR-15) and cost. Day 18 reviews the limit |
| Opening a new chat saves nothing | No empty conversations pile up |
| Fallback replies are recognised by their label | Needs no new column, because `create_all()` can't alter existing tables. Only assistant messages count, so a user can't trigger it by typing the label |

## Files created
- `app/services/chat_service.py`
- `app/forms/chat_forms.py`
- `app/routes/chat.py`
- `app/templates/chat/index.html`
- `app/static/js/chat.js`
- `tests/test_chat.py`
- `documentation/daily_logs/Day13.md`

## Files modified
- `app/models/conversation.py`: messages sort by time, then id, so a question and answer saved in the same moment keep their order
- `app/services/ai_service.py`: `is_fallback_mode()`
- `app/__init__.py`: registers the Blueprint
- `app/static/css/style.css`: chat bubbles and the "Not AI" badge
- `tests/test_frontend.py`: updated for the new link
- `PLAN.md`, `README.md`

## Database changes
- No table changes. The `conversations` and `messages` tables have existed since Day 4.

## Technologies used
- Flask-WTF, Jinja2, Bootstrap, plain JavaScript, Pytest

## Problems encountered and solutions
1. **Problem:** on a phone, the message box ended 22 px below the screen.
   **Found by:** measuring the page in the browser.
   **Cause:** the script scrolled before the page had finished laying out.
   **Solution:** it now scrolls on the `pageshow` event. Measured afterwards: the box ends exactly at the screen edge.

## Test results
- `pytest`: **429 passed, 0 failed, 1 warning** (the known Flask-Login warning). 47 are new.
- Real server with a throwaway database (deleted afterwards), two users, fallback mode:
  - Sent messages were saved in the right order, with the "Not AI" badge and the notice on the page
  - A `<script>` message appeared as plain text; an empty message was refused
  - The second user, with a valid login and CSRF token, got 404 on GET and POST, was sent to a new chat by `/chat`, and the message count didn't change
  - POST without a CSRF token → 400; visitor → 302 to login
- Browser at 375×812: real typing with Shift+Enter and Enter kept both lines and cleared the box; "Thinking..." and the disabled button appeared on send, but not for an empty message; no overflowing elements; Send is 44 px tall; no console errors.
- Browser at 1280×900: measured, with the user's messages on the right and replies on the left, and no overflow. The screenshot at this size was shrunken by the pane.

## Not yet verified
- **A real AI answer on this page.** No API key is set, so real answers were tested with a fake AI in automated tests, and with a stand-in message for how they look.
- **Waiting for a slow answer.** The fallback answers instantly, so "Thinking..." was tested by stopping the form from sending, not during a real wait.

## Outstanding issues
- Older chats can only be reached by their address after starting a new one. The list comes on Day 18.
- Answers are shown as plain text, so any Markdown from the AI appears as symbols (Day 14).
- On narrow screens, the page title is squeezed in the header (Day 26).
- Carried over to Day 24: session cookies identify a user only by id.
- Free disk space is low.

## Git commit
- `Day 13: Add chat interface`

## Next day's objectives (Day 14)
- Question and answer improvements: better error handling and formatted answers

## Completion review
Day 13 is **complete**: users can chat from the page in fallback mode, with the labelling required by FR-56. Real AI answers depend on an API key.
