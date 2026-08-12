from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

DEFAULT_CACHE_DIR = Path(".proofgrid-provider-cache")


class ProviderError(RuntimeError):
    """Base error for a completion provider boundary."""


class TransportError(ProviderError):
    """The request or response transport failed."""


class RateLimited(ProviderError):
    """The provider rejected a request for quota or rate reasons."""


class InvalidResponse(ProviderError):
    """A successful transport returned an unusable completion envelope."""


class NotRecorded(ProviderError):
    """Replay has no fixture for the exact request and will not call live."""


@dataclass(frozen=True)
class Message:
    role: str
    content: str

    def __post_init__(self) -> None:
        if self.role not in {"system", "user", "assistant"}:
            raise ValueError(f"unsupported message role: {self.role!r}")
        if not self.content:
            raise ValueError("message content must not be empty")


@dataclass(frozen=True)
class ChatRequest:
    messages: tuple[Message, ...]
    model: str
    temperature: float = 0.0
    max_tokens: int | None = None
    response_format: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.messages:
            raise ValueError("at least one message is required")
        if not self.model:
            raise ValueError("model must not be empty")
        if self.max_tokens is not None and self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")

    def payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [asdict(message) for message in self.messages],
        }
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens
        if self.response_format is not None:
            payload["response_format"] = self.response_format
        return payload


@dataclass(frozen=True)
class Completion:
    text: str
    provider: str
    model: str
    latency_s: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cached: bool = False


@dataclass(frozen=True)
class Capabilities:
    name: str
    streaming: bool
    tool_calling: bool
    system_prompt: bool
    deterministic: bool
    costs_money: bool


class Provider(Protocol):
    capabilities: Capabilities

    def complete(self, request: ChatRequest, *, timeout: float = 45) -> Completion:
        raise NotImplementedError


def _reported_count(usage: dict[str, Any], key: str) -> int | None:
    value = usage.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float) or value < 0:
        return None
    return int(value)


class OpenAICompatibleProvider:
    capabilities = Capabilities(
        name="openai-compatible",
        streaming=False,
        tool_calling=False,
        system_prompt=True,
        deterministic=False,
        costs_money=True,
    )

    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        *,
        opener: Any | None = None,
    ) -> None:
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("base_url must use http or https")
        self.endpoint = base_url.rstrip("/") + "/chat/completions"
        self.api_key = api_key
        self._opener = opener or urllib.request.urlopen

    def complete(self, request: ChatRequest, *, timeout: float = 45) -> Completion:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        wire_request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(request.payload(), separators=(",", ":")).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        started = time.perf_counter()
        try:
            with self._opener(wire_request, timeout=timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            if exc.code == 429:
                raise RateLimited(detail or "provider returned HTTP 429") from exc
            raise TransportError(f"provider returned HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise TransportError(str(exc)[:300]) from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InvalidResponse(f"provider returned invalid JSON: {exc}") from exc

        try:
            text = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise InvalidResponse("provider response has no message content") from exc
        if not isinstance(text, str) or not text.strip():
            raise InvalidResponse("provider response content must be a non-empty string")
        usage = body.get("usage") or {}
        if not isinstance(usage, dict):
            usage = {}
        return Completion(
            text=text,
            provider=self.capabilities.name,
            model=request.model,
            latency_s=max(0.0, time.perf_counter() - started),
            prompt_tokens=_reported_count(usage, "prompt_tokens"),
            completion_tokens=_reported_count(usage, "completion_tokens"),
            total_tokens=_reported_count(usage, "total_tokens"),
            cached=bool(usage.get("_cached")),
        )


def cache_key(request: ChatRequest) -> str:
    canonical = json.dumps(request.payload(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ReplayProvider:
    capabilities = Capabilities(
        name="replay",
        streaming=False,
        tool_calling=False,
        system_prompt=True,
        deterministic=True,
        costs_money=False,
    )

    def __init__(
        self,
        cache_dir: Path = DEFAULT_CACHE_DIR,
        *,
        record_with: Provider | None = None,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.record_with = record_with

    def _cache_path(self, request: ChatRequest) -> Path:
        key = cache_key(request)
        return self.cache_dir / key[:2] / f"{key}.json"

    def complete(self, request: ChatRequest, *, timeout: float = 45) -> Completion:
        path = self._cache_path(request)
        started = time.perf_counter()
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                text = data["text"]
            except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
                raise InvalidResponse(f"invalid replay fixture: {path}") from exc
            if not isinstance(text, str) or not text.strip():
                raise InvalidResponse(f"replay fixture has empty content: {path}")
            return Completion(
                text=text,
                provider=self.capabilities.name,
                model=request.model,
                latency_s=max(0.0, time.perf_counter() - started),
                cached=True,
            )
        if self.record_with is None:
            raise NotRecorded(
                f"no recording for request {cache_key(request)[:12]}; "
                "configure record_with explicitly to capture it"
            )
        completion = self.record_with.complete(request, timeout=timeout)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {"request": request.payload(), "text": completion.text},
                sort_keys=True,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )
        return completion
