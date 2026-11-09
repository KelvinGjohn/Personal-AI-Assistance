# Development Log — Day 18

| Field | Entry |
|-------|-------|
| Date | 9 November 2026 |
| Day | 18 of 29 |
| Phase | 3 — AI integration (final day) |

## Objectives
- Saved conversations that can be reopened, renamed and deleted
- Review how much of a conversation the AI remembers

## Tasks completed
- `/chat/history` lists the user's chats, most recently used first, with message counts; 20 per page
- `/chat/<id>/rename` with a validated name
- `/chat/<id>/delete` with a confirmation page; deleting removes all of the chat's messages
- The chat page has **All chats**, **New chat**, **Rename** and **Delete** buttons
- The chat page explains: "The assistant remembers the last 20 messages of this chat. Other chats are kept separate."
- History sent to the AI is now limited by size as well as by count

## Review: how much history the AI sees
Day 13 set a limit of 20 messages. That alone is not enough, because 20 long answers could add up to a very large and costly request. Now the AI receives at most the last 20 messages **and** at most 40,000 characters (about 10,000 tokens). The oldest messages are dropped first, and the history still has to begin with a user message. If one old message alone is too large, only the new message is sent.

## How the files connect
`GET /chat/history` → `history()` in `app/routes/chat.py` → `build_conversation_list()` in `app/services/chat_service.py` (one query with `COUNT` and `GROUP BY`) → `paginate_query()` → `chat/history.html`. Rename and delete use `get_user_conversation_or_404()`, like every other module.

## Design decisions
| Decision | Why |
|----------|-----|
| Message counts come from the database with `GROUP BY` | The list doesn't load every message just to count them |
| Deleting relies on the relationship's cascade | All of a chat's messages go with it, and nothing is left behind |
| Another user's chat returns 404 | The same rule as tasks, reminders and notes |
| A size limit as well as a count | Keeps requests fast and their cost predictable |

## Files created
- `app/templates/chat/history.html`, `rename.html`, `confirm_delete.html`
- `tests/test_conversation_memory.py`
- `documentation/daily_logs/Day18.md`

## Files modified
- `app/services/chat_service.py`: `build_conversation_list()`, the size limit on history
- `app/routes/chat.py`: `history()`, `rename()`, `delete()`
- `app/forms/chat_forms.py`: `ConversationTitleForm`
- `app/templates/chat/index.html`: the action buttons and the note about memory
- `PLAN.md`, `README.md`

## Database changes
- None.

## Technologies used
- SQLAlchemy `func.count` with `outerjoin` and `group_by`, Flask-SQLAlchemy pagination, Pytest

## Problems encountered and solutions
1. **Problem:** one new test failed after deleting a chat.
   **Cause:** the test read `conversation.id` from an object whose row had just been deleted.
   **Solution:** the test now stores the ids before deleting.

## Test results
- `pytest`: **622 passed, 0 failed, 1 warning** (the known Flask-Login warning). 41 are new. They cover the list (order, counts, only the user's own chats, pages, bad page numbers), rename (validation, HTML), delete (confirmation, messages removed, other chats kept, what `/chat` opens next), another user getting 404, CSRF, and the size limit on history.
- Real server with a throwaway database (deleted afterwards), two users:
  - The list showed the right chats in the right order, with message counts
  - The second user got 404 on GET and POST for both rename and delete, and the first user's chat and its 4 messages were unchanged
  - Delete without a CSRF token → 400
  - Delete removed the chat and all its messages, and left the other chat's messages untouched; `/chat` then opened the remaining chat
- Browser at 375×812: the four buttons are 44 px tall and wrap neatly; the list opened from **All chats**; renaming through the form worked; no overflowing elements; no console errors.

## Outstanding issues
- Renaming a chat counts as using it, so it moves to the top of the list.
- Carried over to Day 24: session cookies identify a user only by id; AI suggestions aren't counted in the message limit.

## Git commit
- `Day 18: Add saved chats with rename and delete`

## Next day's objectives (Day 19)
- Phase 4 begins: in-app notifications, including due reminders, with mark as read

## Completion review
Day 18 is **complete**, and with it **Phase 3**. The AI can chat, format answers, create tasks and reminders with confirmation, answer from the user's own data when allowed, and remember conversations, all with a labelled fallback when no key is set.
