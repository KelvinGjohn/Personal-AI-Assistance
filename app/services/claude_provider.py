"""
Claude provider: sends messages to the Anthropic API using the official SDK.

To add another provider later, write a class like this one with a name and an
ask() method, then add it to get_provider() in ai_service.py.
"""

import anthropic
from flask import current_app

from app.services.ai_service import AIResponse, AIServiceError

DEFAULT_MODEL = "claude-opus-5-5"
MAX_ANSWER_TOKENS = 16000
TIMEOUT_SECONDS = 120.0  # A web page shouldn't wait for ever
MAX_RETRIES = 1

# These models accept the server-side fallback described in ClaudeProvider.ask()
MODELS_WITH_SERVER_FALLBACK = {"claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}


class ClaudeProvider:
    name = "claude"

    def __init__(self, api_key, model=DEFAULT_MODEL, http_client=None):
        # The key is always passed in, so the SDK can't quietly use some other
        # credential on this computer and charge it. http_client is for tests.
        self.client = anthropic.Anthropic(
            api_key=api_key,
            timeout=TIMEOUT_SECONDS,
            max_retries=MAX_RETRIES,
            http_client=http_client,
        )
        self.model = model

    def ask(self, messages, system):
        options = {}
        if self.model in MODELS_WITH_SERVER_FALLBACK:
            # If a safety check declines the request, Anthropic retries it on
            # another suitable model instead of returning a refusal straight away
            options = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}

        try:
            response = self.client.beta.messages.create(
                model=self.model,
                max_tokens=MAX_ANSWER_TOKENS,
                system=system,
                messages=messages,
                thinking={"type": "adaptive"},
                output_config={"effort": "medium"},
                **options,
            )
        except anthropic.APIError as error:
            raise AIServiceError(self._friendly_message(error)) from error

        if response.stop_reason == "refusal":
            raise AIServiceError("The AI can't help with that request. Please try asking differently.")

        # An answer is a list of blocks, and only some of them are text
        text = "".join(block.text for block in response.content if block.type == "text").strip()
        if not text:
            raise AIServiceError("The AI didn't return an answer. Please try again.")

        return AIResponse(
            text=text,
            provider=self.name,
            is_cut_off=response.stop_reason == "max_tokens",
        )

    def _friendly_message(self, error):
        """
        Turn an SDK error into a message for users. Details go only to the log,
        and never the conversation, since it may be private.
        Most specific errors come first, because some inherit from others.
        """
        status = getattr(error, "status_code", None)
        current_app.logger.warning("Claude API error: %s (status %s)", type(error).__name__, status)

        if isinstance(error, anthropic.APITimeoutError):
            return "The AI took too long to answer. Please try again."
        if isinstance(error, anthropic.APIConnectionError):
            return "The AI service can't be reached right now. Please try again later."
        if isinstance(error, anthropic.RateLimitError):
            return "The AI service is busy. Please wait a moment and try again."
        if isinstance(error, (anthropic.InternalServerError,)) or status == 529:
            return "The AI service is having a problem. Please try again later."
        if isinstance(error, (anthropic.AuthenticationError, anthropic.PermissionDeniedError)):
            return "The AI service isn't set up correctly. Please check the API key."
        return "The AI service couldn't process that request. Please check its settings or try again."
