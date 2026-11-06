"""
AI service: the one place the rest of the app calls to get an AI answer.

Other code only uses ask_ai(). It doesn't know which provider answered, so a
provider can be changed in .env without touching routes or templates.

If no provider is set up, a fallback answers instead. The fallback is not AI
and always says so: is_fallback is True and its text starts with FALLBACK_LABEL.
"""

from dataclasses import dataclass

from flask import current_app

FALLBACK_LABEL = "Development mode - this is not an AI answer."

SYSTEM_PROMPT = (
    "You are a personal assistant inside a productivity web app. "
    "Answer clearly and briefly, in plain language. "
    "The app shows simple Markdown: bold, italics, lists, code blocks, tables and web links. "
    "It doesn't show images or raw HTML, so don't use them."
)


@dataclass
class AIResponse:
    """An answer from ask_ai()."""

    text: str
    provider: str
    is_fallback: bool = False
    is_cut_off: bool = False  # True if the answer hit the length limit


class AIServiceError(Exception):
    """
    The AI couldn't answer. The message is safe to show to users: it never
    contains API keys or the provider's raw error text.
    """


class FallbackProvider:
    """Used when no AI provider is set up, so the rest of the app can still be tested."""

    name = "fallback"

    def __init__(self, reason):
        self.reason = reason

    def ask(self, messages, system):
        return AIResponse(
            text=f"{FALLBACK_LABEL} {self.reason}",
            provider=self.name,
            is_fallback=True,
        )


def get_provider():
    """Choose the provider from the settings in .env."""
    name = current_app.config["AI_PROVIDER"].strip().lower()
    api_key = current_app.config["AI_API_KEY"].strip()

    if name == "fallback":
        return FallbackProvider("No AI provider is configured.")

    if name == "claude":
        if not api_key:
            current_app.logger.warning("AI_PROVIDER is claude, but AI_API_KEY is empty.")
            return FallbackProvider("The AI provider has no API key.")

        # Imported here so that the app starts without it in fallback mode
        from app.services.claude_provider import DEFAULT_MODEL, ClaudeProvider

        model = current_app.config["AI_MODEL"].strip() or DEFAULT_MODEL
        return ClaudeProvider(api_key=api_key, model=model)

    # A typing mistake in .env shouldn't stop tasks, notes and the rest from working
    current_app.logger.warning("Unknown AI_PROVIDER: %r. Using the fallback.", name)
    return FallbackProvider("The AI provider setting is not recognised.")


def is_fallback_mode():
    """True if questions will be answered by the fallback, not by an AI."""
    return isinstance(get_provider(), FallbackProvider)


def ask_ai(messages, system=SYSTEM_PROMPT):
    """
    Send a conversation to the AI and return an AIResponse.

    messages is a list such as [{"role": "user", "content": "Hello"}], with the
    newest message last. Raises AIServiceError if the AI can't answer.
    """
    if not messages or messages[-1]["role"] != "user" or not messages[-1]["content"].strip():
        raise AIServiceError("Please enter a message.")

    return get_provider().ask(messages, system)
