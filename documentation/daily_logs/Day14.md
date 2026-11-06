# Development Log — Day 14

| Field | Entry |
|-------|-------|
| Date | 6 November 2026 |
| Day | 14 of 29 |
| Phase | 3 — AI integration |

## Objectives
- Show AI answers with formatting
- Improve error handling in the chat

## Tasks completed
- AI answers in Markdown are shown formatted: bold, italics, lists, code blocks, tables, quotes and links
- Every formatted answer passes through a sanitizer, so nothing in an answer can run in the browser
- User messages and fallback replies stay plain text
- AI errors appear next to the message box, not at the top of the page
- A limit of 50 messages per user per hour, checked before the AI is called
- An answer that hits the length limit is saved with a note saying it was cut short
- The system prompt tells the AI which formatting the app can show

## How the files connect
`chat/index.html` → the `markdown` template filter → `render_markdown()` in `app/formatting.py` → the Markdown library converts the text to HTML → nh3 removes everything not on the allowed list → the result is marked safe for Jinja. In `send_message()`, `count_recent_messages()` runs before `ask_ai()`.

## Design decisions
| Decision | Why |
|----------|-----|
| Markdown, then a sanitizer with a short allowed list | Markdown lets HTML through, so the cleaning step is what makes the output safe |
| My own allowed list instead of nh3's default | The default allows images, and an image loads from another website, which could track readers |
| Only `http`, `https` and `mailto` links, and no links to this app's own pages | Blocks `javascript:` links and stops an answer from pointing users at app actions |
| Links get `rel="noopener noreferrer nofollow"` | A linked site can't control this page or see where the click came from |
| Only assistant answers are formatted | User messages are shown exactly as typed |
| Code blocks and tables scroll inside the bubble | A long line can't widen the page on a phone |
| Message limit per user, also in fallback mode | Each AI answer costs money, and the rule should behave the same whether or not a key is set |
| The error appears inside the form | On a long chat the top of the page is off screen |

## Files created
- `app/formatting.py`
- `tests/test_question_answer.py`
- `documentation/daily_logs/Day14.md`

## Files modified
- `app/__init__.py`: registers the `markdown` filter
- `app/routes/chat.py`: passes the error to the page instead of using `flash()`
- `app/services/chat_service.py`: message limit, cut-off note
- `app/services/ai_service.py`: system prompt mentions formatting
- `app/templates/chat/index.html`: formatted answers, error by the box
- `app/static/css/style.css`: styles for formatted answers
- `requirements.txt`: `Markdown`, `nh3`
- `PLAN.md`, `README.md`

## Database changes
- None. The cut-off note is part of the saved text.

## Technologies used
- Python-Markdown, nh3 (HTML sanitizer), MarkupSafe, Pytest

## Problems encountered and solutions
1. **Checked before writing code:** with the real libraries, Markdown passed `<script>` straight through, and nh3's default list kept `<img>`. This is why the app uses its own allowed list.
2. **Browser check:** after sending a message that failed, the error was below the bottom of the phone screen, and the page was at the top.
   **Investigation:** the browser pane was hidden at the time. In that state the page couldn't scroll at all: even `window.scrollTo(0, 150)` left it at 0.
   **Result:** no code was changed. The page is meant to scroll to the bottom of the form, which contains the error. That scroll was measured working on Day 13, but it couldn't be confirmed today.

## Test results
- `pytest`: **471 passed, 0 failed, 1 warning** (the known Flask-Login warning). 42 are new. They cover each kind of formatting, 14 kinds of harmful content, user messages staying plain text, the cut-off note, the error position, and the message limit (per user, old messages, the boundary, and that the AI isn't called).
- Real server, with an obviously fake key sent to Anthropic: the request was refused (401); the friendly error appeared inside the form, the text was kept, and no messages were saved. This was tried both by script and by typing in the browser.
- Browser at 375×812, with a formatting-heavy answer containing an attack: bold, italics, numbered list, code block, table, quote and link all displayed; the code block scrolled inside the bubble while the page stayed 375 px wide; no `<script>` or `<img>` reached the page and the page title wasn't changed; the user's `**text**` and `<b>` stayed plain; no console errors.

## Not yet verified
- Whether the error is scrolled into view on a phone after a failed send (see problem 2).
- Formatting of real Claude answers. The formatting was tested with a written example, because no API key is set.

## Outstanding issues
- Older chats list (Day 18).
- Carried over to Day 24: session cookies identify a user only by id.
- Free disk space is low.

## Git commit
- `Day 14: Add formatted answers and chat error handling`

## Next day's objectives (Day 15)
- AI task assistance: turn a plain-language request into a task, shown for confirmation before it is saved (FR-53)

## Completion review
Day 14 is **complete**: answers are formatted safely and errors are handled clearly. One display detail on phones remains to be confirmed.
