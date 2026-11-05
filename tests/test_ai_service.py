"""
Day 12 - tests for the AI service.

No test here contacts Anthropic. The real SDK runs, but its network layer is
replaced by fake_api, which records each request and returns a chosen answer.
That way the request we send and the errors the SDK raises are both real.
"""

import json
import logging

import anthropic
import httpx2
import pytest

from app.services.ai_service import (
    FALLBACK_LABEL,
    SYSTEM_PROMPT,
    AIServiceError,
    FallbackProvider,
    ask_ai,
    get_provider,
)
from app.services.claude_provider import DEFAULT_MODEL, ClaudeProvider

FAKE_KEY = "fake-key-for-tests-only"
HELLO = [{"role": "user", "content": "Hello"}]


def api_reply(content=None, stop_reason="end_turn"):
    """The JSON the Anthropic API returns for a successful request."""
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": DEFAULT_MODEL,
        "content": [{"type": "text", "text": "Hi there"}] if content is None else content,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {"input_tokens": 5, "output_tokens": 5},
    }


class FakeAPI:
    def __init__(self, status=200, body=None, error=None):
        self.status = status
        self.body = api_reply() if body is None else body
        self.error = error
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        if self.error:
            raise self.error
        return httpx2.Response(self.status, json=self.body)

    @property
    def last_body(self):
        return json.loads(self.requests[-1].content)


def make_provider(fake_api, model=DEFAULT_MODEL):
    http_client = anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(fake_api))
    return ClaudeProvider(api_key=FAKE_KEY, model=model, http_client=http_client)


@pytest.fixture
def no_retries(monkeypatch):
    """Errors that would be retried shouldn't make the tests wait."""
    monkeypatch.setattr("app.services.claude_provider.MAX_RETRIES", 0)


# ---------- Choosing a provider ----------

def test_tests_never_use_a_real_provider_or_key(app):
    assert app.config["AI_PROVIDER"] == "fallback"
    assert app.config["AI_API_KEY"] == ""


@pytest.mark.parametrize("name, key, reason", [
    ("fallback", "", "No AI provider is configured."),
    ("fallback", FAKE_KEY, "No AI provider is configured."),
    ("claude", "", "The AI provider has no API key."),
    ("claude", "   ", "The AI provider has no API key."),
    ("nonsense", FAKE_KEY, "not recognised"),
])
def test_fallback_is_used_unless_a_provider_is_fully_set_up(app, name, key, reason):
    app.config.update(AI_PROVIDER=name, AI_API_KEY=key)
    provider = get_provider()
    assert isinstance(provider, FallbackProvider)
    assert reason in provider.reason


@pytest.mark.parametrize("name", ["claude", "CLAUDE", " Claude "])
def test_claude_is_chosen_with_a_key(app, name):
    app.config.update(AI_PROVIDER=name, AI_API_KEY=FAKE_KEY)
    provider = get_provider()
    assert isinstance(provider, ClaudeProvider)
    assert provider.model == DEFAULT_MODEL


def test_model_can_be_changed_in_settings(app):
    app.config.update(AI_PROVIDER="claude", AI_API_KEY=FAKE_KEY, AI_MODEL="claude-haiku-5-5")
    assert get_provider().model == "claude-haiku-5-5"


def test_missing_key_never_falls_through_to_another_credential_on_the_computer(app, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "some-other-key")
    app.config.update(AI_PROVIDER="claude", AI_API_KEY="")
    assert isinstance(get_provider(), FallbackProvider)


# ---------- The fallback ----------

def test_fallback_answer_is_clearly_labelled_as_not_ai(app):
    response = ask_ai(HELLO)
    assert response.is_fallback is True
    assert response.provider == "fallback"
    assert response.text.startswith(FALLBACK_LABEL)
    assert "not an AI answer" in response.text


def test_fallback_does_not_pretend_to_answer_or_repeat_the_message(app):
    response = ask_ai([{"role": "user", "content": "What is the capital of France?"}])
    assert "Paris" not in response.text
    assert "France" not in response.text


# ---------- Checking the message ----------

@pytest.mark.parametrize("messages", [
    [],
    None,
    [{"role": "user", "content": ""}],
    [{"role": "user", "content": "    "}],
    [{"role": "assistant", "content": "The last message must come from the user"}],
])
def test_empty_or_invalid_messages_are_rejected(app, messages):
    with pytest.raises(AIServiceError, match="Please enter a message."):
        ask_ai(messages)


# ---------- The request sent to Claude ----------

def test_request_contents(app):
    fake_api = FakeAPI()
    make_provider(fake_api).ask(HELLO, SYSTEM_PROMPT)
    body = fake_api.last_body
    assert body["model"] == "claude-opus-5-5"
    assert body["messages"] == HELLO
    assert body["system"] == SYSTEM_PROMPT
    assert body["max_tokens"] == 16000
    assert body["thinking"] == {"type": "adaptive"}
    assert body["output_config"] == {"effort": "medium"}


def test_request_goes_to_anthropic_over_https_with_the_key_in_a_header(app):
    fake_api = FakeAPI()
    make_provider(fake_api).ask(HELLO, SYSTEM_PROMPT)
    request = fake_api.requests[-1]
    assert request.url.scheme == "https"
    assert request.url.host == "api.anthropic.com"
    # The SDK chooses the header name; what matters is that the key is only in a header
    assert any(FAKE_KEY in value for value in request.headers.values())
    assert FAKE_KEY not in str(request.url)
    assert FAKE_KEY not in request.content.decode()


def test_only_the_given_messages_are_sent(app):
    """The privacy rule (NFR-15): nothing else about the user goes to the provider."""
    fake_api = FakeAPI()
    make_provider(fake_api).ask(HELLO, SYSTEM_PROMPT)
    assert set(fake_api.last_body) == {
        "model", "max_tokens", "system", "messages", "thinking", "output_config", "fallbacks",
    }


def test_server_side_fallback_is_on_for_the_default_model(app):
    fake_api = FakeAPI()
    make_provider(fake_api).ask(HELLO, SYSTEM_PROMPT)
    assert fake_api.last_body["fallbacks"] == "default"
    assert "server-side-fallback-2026-07-01" in fake_api.requests[-1].headers["anthropic-beta"]


def test_server_side_fallback_is_left_out_for_models_without_it(app):
    fake_api = FakeAPI()
    make_provider(fake_api, model="claude-haiku-5-5").ask(HELLO, SYSTEM_PROMPT)
    assert "fallbacks" not in fake_api.last_body
    assert "anthropic-beta" not in fake_api.requests[-1].headers


# ---------- Reading the answer ----------

def test_answer_is_returned_as_real_ai(app):
    response = make_provider(FakeAPI()).ask(HELLO, SYSTEM_PROMPT)
    assert response.text == "Hi there"
    assert response.provider == "claude"
    assert response.is_fallback is False
    assert response.is_cut_off is False


def test_only_text_blocks_are_used(app):
    content = [
        {"type": "thinking", "thinking": "", "signature": "abc"},
        {"type": "text", "text": "Part one. "},
        {"type": "text", "text": "Part two."},
    ]
    response = make_provider(FakeAPI(body=api_reply(content))).ask(HELLO, SYSTEM_PROMPT)
    assert response.text == "Part one. Part two."


def test_answer_that_hit_the_length_limit_is_marked(app):
    body = api_reply(stop_reason="max_tokens")
    assert make_provider(FakeAPI(body=body)).ask(HELLO, SYSTEM_PROMPT).is_cut_off is True


@pytest.mark.parametrize("content", [[], [{"type": "text", "text": "   "}]])
def test_empty_answer_is_an_error(app, content):
    with pytest.raises(AIServiceError, match="didn't return an answer"):
        make_provider(FakeAPI(body=api_reply(content))).ask(HELLO, SYSTEM_PROMPT)


def test_refusal_is_a_clear_error_even_with_partial_text(app):
    body = api_reply([{"type": "text", "text": "Partial"}], stop_reason="refusal")
    with pytest.raises(AIServiceError, match="can't help with that request"):
        make_provider(FakeAPI(body=body)).ask(HELLO, SYSTEM_PROMPT)


# ---------- Errors ----------

def error_body(error_type, message):
    return {"type": "error", "error": {"type": error_type, "message": message}}


@pytest.mark.parametrize("status, error_type, expected", [
    (400, "invalid_request_error", "couldn't process that request"),
    (401, "authentication_error", "check the API key"),
    (402, "billing_error", "couldn't process that request"),
    (403, "permission_error", "check the API key"),
    (404, "not_found_error", "couldn't process that request"),
    (429, "rate_limit_error", "busy"),
    (500, "api_error", "having a problem"),
    (529, "overloaded_error", "having a problem"),
])
def test_api_errors_become_friendly_messages(app, no_retries, status, error_type, expected):
    fake_api = FakeAPI(status=status, body=error_body(error_type, "secret raw detail"))
    with pytest.raises(AIServiceError) as caught:
        make_provider(fake_api).ask(HELLO, SYSTEM_PROMPT)
    assert expected in str(caught.value)
    assert "secret raw detail" not in str(caught.value)
    assert FAKE_KEY not in str(caught.value)


@pytest.mark.parametrize("network_error, expected", [
    (httpx2.ConnectError("no route"), "can't be reached"),
    (httpx2.ReadTimeout("slow"), "too long"),
])
def test_network_problems_become_friendly_messages(app, no_retries, network_error, expected):
    with pytest.raises(AIServiceError, match=expected):
        make_provider(FakeAPI(error=network_error)).ask(HELLO, SYSTEM_PROMPT)


def test_log_has_the_error_type_but_not_the_message_or_key(app, no_retries, caplog):
    private = "my private question"
    fake_api = FakeAPI(status=401, body=error_body("authentication_error", "bad key"))
    with caplog.at_level(logging.WARNING), pytest.raises(AIServiceError):
        make_provider(fake_api).ask([{"role": "user", "content": private}], SYSTEM_PROMPT)
    assert "AuthenticationError" in caplog.text
    assert private not in caplog.text
    assert FAKE_KEY not in caplog.text


def test_temporary_error_is_retried_once(app, monkeypatch):
    # Without this the SDK waits before retrying, which only slows the test down
    monkeypatch.setattr("anthropic._base_client.BaseClient._calculate_retry_timeout",
                        lambda *args, **kwargs: 0)
    fake_api = FakeAPI(status=500, body=error_body("api_error", "oops"))
    with pytest.raises(AIServiceError):
        make_provider(fake_api).ask(HELLO, SYSTEM_PROMPT)
    assert len(fake_api.requests) == 2


# ---------- The rest of the app ----------

def test_app_works_while_the_ai_provider_is_down(app, auth_client):
    """NFR-11: an AI failure must not affect anything else."""
    app.config.update(AI_PROVIDER="claude", AI_API_KEY=FAKE_KEY)
    for path in ("/", "/tasks", "/reminders", "/notes", "/settings", "/health"):
        assert auth_client.get(path).status_code == 200
