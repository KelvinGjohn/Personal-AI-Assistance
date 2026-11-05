# Development Log — Day 12

| Field | Entry |
|-------|-------|
| Date | 5 November 2026 |
| Day | 12 of 29 |
| Phase | 3 — AI integration |

## Objectives
- Build the AI service foundation
- Make the AI provider configurable
- Provide a clearly labelled fallback when no provider is set up

## Tasks completed
- `app/services/ai_service.py`: `ask_ai()`, the one function the rest of the app calls; `AIResponse`, `AIServiceError`, `FallbackProvider`, `get_provider()`
- `app/services/claude_provider.py`: the Claude provider, using the official Anthropic SDK
- `scripts/check_ai.py`: checks the AI setup from the command line
- `TestingConfig` forces the fallback, so tests can never spend money or send data, even if `.env` holds a real key
- `.env.example` and the README explain how to turn on real AI

## Provider decision
Day 1 left the provider choice for today. The developer chose **Claude**, using the `claude-opus-5-5` model. It can be changed with `AI_MODEL`, and another provider can be added as one new class, without changing any routes or templates.

## How the files connect
Later: chat route → `ask_ai(messages)` → `get_provider()` reads `AI_PROVIDER`, `AI_API_KEY` and `AI_MODEL` → `FallbackProvider` or `ClaudeProvider` → `AIResponse`, or `AIServiceError` with a message that is safe to show users.

## Design decisions
| Decision | Why |
|----------|-----|
| The fallback says "this is not an AI answer" and doesn't try to answer | FR-56: it must never pass as real AI |
| A missing key or a mistyped provider uses the fallback | NFR-11: AI settings can't stop tasks, notes and the rest from working |
| The key from `.env` is always passed to the SDK explicitly | Otherwise the SDK could quietly use another credential on the computer and charge it |
| Provider errors become friendly messages | Users never see raw errors or keys |
| Logs hold the error type and status only | Conversations may be private |
| Only the given messages and settings are sent | NFR-15: minimum data goes to the provider |
| Server-side fallback (`fallbacks: "default"`) is on | If a safety check declines a request, Anthropic retries on another suitable model. Can be removed if not wanted |
| 120-second timeout and 1 retry | A web page shouldn't wait for many minutes |
| The SDK is imported only when Claude is used | The app starts and runs in fallback mode without it |

## Files created
- `app/services/ai_service.py`, `app/services/claude_provider.py`
- `scripts/check_ai.py`
- `tests/test_ai_service.py`
- `documentation/daily_logs/Day12.md`

## Files modified
- `config/settings.py`: comments; AI settings forced off for tests
- `.env.example`: how to configure the provider
- `requirements.txt`: added `anthropic==2.5.0`; removed `requests`, which was reserved for calling the AI provider and is no longer needed by the app
- `PLAN.md`, `README.md`

## Database changes
- None.

## Technologies used
- Anthropic Python SDK, Python dataclasses, `httpx2.MockTransport` (fake network layer in tests), Pytest

## Problems encountered and solutions
1. **Problem:** one test expected the API key in an `x-api-key` header.
   **Cause:** I assumed the header name from memory. SDK 2.5.0 sends `Authorization: Bearer`.
   **Solution:** the test now checks what matters: the key is in a header, and never in the URL or body.
2. **Problem:** Git and the Bash tool stopped working partway through the day.
   **Cause:** Git is no longer installed on this PC.
   **Solution:** the code was finished and tested without Git. The commit waits until Git is reinstalled. The history is safe in `.git` and on GitHub.
3. **Problem:** free disk space fell as low as 0.32 GB.
   **Solution:** the developer cleared space (0.89 GB free at the end of the session). The SDK used 43 MB, installed without pip's cache.

## Test results
- `pytest`: **382 passed, 0 failed, 1 warning** (the known Flask-Login warning). 42 are new. They use the real SDK with a fake network layer and cover the request contents, reading answers, refusals, empty answers, every error type, retries, and what is logged.
- `check_ai.py` with no provider: answered with the labelled fallback and didn't answer the question.
- `check_ai.py` with an unrecognised provider: labelled fallback.
- `check_ai.py` with a fake key over the real network: Anthropic returned 401, and the script showed the friendly message.

## Not yet verified
- **A successful answer from the real API.** No API key is available yet, so the real connection is proven only as far as Anthropic rejecting a fake key. Run `python scripts/check_ai.py` once a key is set.

## Outstanding issues
- Length limits on messages and chat formatting are planned for Day 14.
- Carried over to Day 24: session cookies identify a user only by id.
- Free disk space is low.

## Git commit
- `Day 12: Add AI service with Claude provider and fallback`

## Next day's objectives (Day 13)
- Working chat page that uses `ask_ai()`
- Fallback answers clearly labelled on the page

## Completion review
Day 12 is **complete** for the fallback and for all logic that can be tested without a key. A real answer from Claude remains to be confirmed once a key is set.
