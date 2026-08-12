from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from proofgrid_provider import (
    ChatRequest,
    InvalidResponse,
    Message,
    NotRecorded,
    OpenAICompatibleProvider,
    RateLimited,
    ReplayProvider,
    TransportError,
)


def request() -> ChatRequest:
    return ChatRequest(
        messages=(
            Message("system", "Return a grounded answer."),
            Message("user", "Summarize the incident."),
        ),
        model="test-model",
        temperature=0,
        max_tokens=120,
        response_format={"type": "json_object"},
    )


class FakeResponse:
    def __init__(self, body: object) -> None:
        self.body = body

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.body).encode("utf-8")


def test_http_preserves_request_auth_and_reported_usage() -> None:
    captured: dict[str, object] = {}

    def opener(wire: urllib.request.Request, *, timeout: float) -> FakeResponse:
        captured["url"] = wire.full_url
        captured["headers"] = dict(wire.header_items())
        captured["payload"] = json.loads(bytes(wire.data or b"").decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse(
            {
                "choices": [{"message": {"content": '{"intent":"billing"}'}}],
                "usage": {
                    "prompt_tokens": 19,
                    "completion_tokens": 7,
                    "total_tokens": 26,
                },
            }
        )

    completion = OpenAICompatibleProvider("https://model.example/v1", "secret", opener=opener).complete(
        request(), timeout=12
    )

    assert captured["url"] == "https://model.example/v1/chat/completions"
    assert captured["timeout"] == 12
    assert captured["headers"]["Authorization"] == "Bearer secret"
    payload = captured["payload"]
    assert payload["messages"] == [
        {"role": "system", "content": "Return a grounded answer."},
        {"role": "user", "content": "Summarize the incident."},
    ]
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["temperature"] == 0
    assert (completion.prompt_tokens, completion.completion_tokens, completion.total_tokens) == (
        19,
        7,
        26,
    )


def test_empty_key_omits_authorization_and_invalid_usage_is_not_invented() -> None:
    captured: dict[str, str] = {}

    def opener(wire: urllib.request.Request, *, timeout: float) -> FakeResponse:
        del timeout
        captured.update(dict(wire.header_items()))
        return FakeResponse(
            {
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": True, "completion_tokens": -1, "total_tokens": "9"},
            }
        )

    completion = OpenAICompatibleProvider("https://model.example/v1", opener=opener).complete(request())
    assert "Authorization" not in captured
    assert completion.prompt_tokens is None
    assert completion.completion_tokens is None
    assert completion.total_tokens is None


def http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://model.example/v1/chat/completions",
        code,
        "failure",
        {},
        io.BytesIO(b"provider detail"),
    )


def test_rate_limit_is_distinct_from_other_http_failures() -> None:
    def limited(*_args: object, **_kwargs: object) -> FakeResponse:
        raise http_error(429)

    def failed(*_args: object, **_kwargs: object) -> FakeResponse:
        raise http_error(503)

    with pytest.raises(RateLimited, match="provider detail"):
        OpenAICompatibleProvider("https://model.example/v1", opener=limited).complete(request())
    with pytest.raises(TransportError, match="HTTP 503"):
        OpenAICompatibleProvider("https://model.example/v1", opener=failed).complete(request())


def test_url_failure_is_normalized() -> None:
    def failed(*_args: object, **_kwargs: object) -> FakeResponse:
        raise urllib.error.URLError("offline")

    with pytest.raises(TransportError, match="offline"):
        OpenAICompatibleProvider("https://model.example/v1", opener=failed).complete(request())


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"choices": []},
        {"choices": [{"message": {}}]},
        {"choices": [{"message": {"content": ""}}]},
        {"choices": [{"message": {"content": None}}]},
    ],
)
def test_malformed_success_envelope_is_rejected(body: object) -> None:
    provider = OpenAICompatibleProvider(
        "https://model.example/v1", opener=lambda *_args, **_kwargs: FakeResponse(body)
    )
    with pytest.raises(InvalidResponse):
        provider.complete(request())


def test_replay_uses_instance_directory_and_never_falls_through(tmp_path: Path) -> None:
    replay = ReplayProvider(tmp_path)
    with pytest.raises(NotRecorded):
        replay.complete(request())

    class Recorder:
        capabilities = replay.capabilities
        calls = 0

        def complete(self, incoming: ChatRequest, *, timeout: float = 45):
            del timeout
            self.calls += 1
            return OpenAICompatibleProvider(
                "https://model.example/v1",
                opener=lambda *_args, **_kwargs: FakeResponse({"choices": [{"message": {"content": incoming.model}}]}),
            ).complete(incoming)

    recorder = Recorder()
    recording = ReplayProvider(tmp_path, record_with=recorder)
    assert recording.complete(request()).text == "test-model"
    assert recorder.calls == 1
    first = replay.complete(request())
    second = replay.complete(request())
    assert first.text == second.text == "test-model"
    assert first.cached and second.cached
    assert recorder.calls == 1
    assert len(list(tmp_path.rglob("*.json"))) == 1


def test_cache_key_covers_request_settings(tmp_path: Path) -> None:
    replay = ReplayProvider(tmp_path)
    changed = ChatRequest(
        messages=request().messages,
        model=request().model,
        temperature=0.5,
        response_format=request().response_format,
    )
    assert replay._cache_path(request()) != replay._cache_path(changed)
