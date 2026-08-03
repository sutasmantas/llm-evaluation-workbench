from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from .models import Candidate, EvalCase, ProviderResult


class ProviderError(RuntimeError):
    """A normalized provider failure."""


def _normalize_enum(value: str | None, allowed: set[str], aliases: dict[str, str]) -> str:
    if not value:
        return "unknown"
    lowered = value.strip().lower()
    normalized = aliases.get(lowered, lowered)
    return normalized if normalized in allowed else "unknown"


def _field(source: str, label: str) -> str | None:
    match = re.search(rf"(?im)^\s*{re.escape(label)}\s*:\s*(.+?)\s*$", source)
    return match.group(1).strip() if match else None


def _baseline_extract(source: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    mapping = {
        "contact_name": "Name",
        "company": "Company",
        "region": "Region",
        "intent": "Need",
        "urgency": "Urgency",
        "follow_up": "Follow-up",
    }
    for key, label in mapping.items():
        value = _field(source, label)
        if value and value.lower() not in {"none", "not stated", "n/a"}:
            result[key] = value
    return result


def _structured_extract(source: str, repair: bool) -> dict[str, Any]:
    baseline = _baseline_extract(source)
    urgency_aliases = {"urgent": "high", "asap": "high", "normal": "medium", "not urgent": "low"}
    intent_aliases = {
        "book a demo": "demo",
        "demo": "demo",
        "crm integration": "integration",
        "integration": "integration",
        "support request": "support",
        "support": "support",
    }
    region_aliases = {"europe": "eu", "european union": "eu", "united states": "us", "asia pacific": "apac"}
    follow_up = baseline.get("follow_up")
    if follow_up:
        lowered = follow_up.lower()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", follow_up):
            normalized_date: str | None = follow_up
        elif lowered in {"7 aug 2026", "august 7, 2026"}:
            normalized_date = "2026-08-07"
        elif "next friday" in lowered:
            normalized_date = None if repair else "2026-08-07"
        else:
            normalized_date = None
    else:
        normalized_date = None

    return {
        "contact_name": baseline.get("contact_name"),
        "company": baseline.get("company"),
        "region": _normalize_enum(baseline.get("region"), {"eu", "us", "apac", "unknown"}, region_aliases),
        "intent": _normalize_enum(
            baseline.get("intent"), {"demo", "integration", "support", "unknown"}, intent_aliases
        ),
        "urgency": _normalize_enum(baseline.get("urgency"), {"high", "medium", "low", "unknown"}, urgency_aliases),
        "follow_up": normalized_date,
    }


class DeterministicAdapter:
    """A no-key fixture adapter. It proves orchestration, not model quality."""

    provider_id = "deterministic-local"

    def generate(self, candidate: Candidate, case: EvalCase) -> ProviderResult:
        started = time.perf_counter()
        retry_count = 0
        rate_limit_count = 0
        simulated = set(candidate.metadata.get("simulate_rate_limit_case_ids", []))
        if case.case_id in simulated and candidate.max_retries > 0:
            retry_count = 1
            rate_limit_count = 1

        if candidate.response_mode == "baseline":
            payload = _baseline_extract(case.input)
        elif candidate.response_mode == "structured":
            payload = _structured_extract(case.input, repair=False)
        elif candidate.response_mode == "repair":
            payload = _structured_extract(case.input, repair=True)
        else:
            return ProviderResult(
                output=None,
                latency_ms=(time.perf_counter() - started) * 1000,
                error=f"unsupported deterministic response_mode: {candidate.response_mode}",
                failure_class="configuration",
            )

        output = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return ProviderResult(
            output=output,
            latency_ms=(time.perf_counter() - started) * 1000,
            cost_usd=0.0,
            retry_count=retry_count,
            rate_limit_count=rate_limit_count,
        )


@dataclass(frozen=True)
class OpenAICompatibleConfig:
    base_url: str
    api_key: str
    model: str
    timeout_seconds: float = 20.0
    max_retries: int = 2
    retry_delay_seconds: float = 0.0
    input_cost_per_million: float | None = None
    output_cost_per_million: float | None = None


class OpenAICompatibleAdapter:
    """Small chat-completions boundary with bounded transient retries."""

    provider_id = "openai-compatible"

    def __init__(
        self,
        config: OpenAICompatibleConfig,
        opener: Callable[..., Any] | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if not config.base_url.startswith(("http://", "https://")):
            raise ValueError("base_url must use http or https")
        self.config = config
        self._opener = opener or urllib.request.urlopen
        self._sleeper = sleeper

    def generate(self, candidate: Candidate, case: EvalCase) -> ProviderResult:
        started = time.perf_counter()
        retries = 0
        rate_limits = 0
        body = json.dumps(
            {
                "model": candidate.model or self.config.model,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": candidate.prompt},
                    {"role": "user", "content": case.input},
                ],
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self.config.base_url.rstrip("/") + "/chat/completions",
            data=body,
            headers={"Authorization": f"Bearer {self.config.api_key}", "Content-Type": "application/json"},
            method="POST",
        )

        for attempt in range(self.config.max_retries + 1):
            try:
                with self._opener(request, timeout=self.config.timeout_seconds) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                content = payload["choices"][0]["message"]["content"]
                usage = payload.get("usage") or {}
                prompt_tokens = usage.get("prompt_tokens")
                completion_tokens = usage.get("completion_tokens")
                total_tokens = usage.get("total_tokens")
                cost = None
                if (
                    prompt_tokens is not None
                    and completion_tokens is not None
                    and self.config.input_cost_per_million is not None
                    and self.config.output_cost_per_million is not None
                ):
                    cost = (
                        prompt_tokens * self.config.input_cost_per_million
                        + completion_tokens * self.config.output_cost_per_million
                    ) / 1_000_000
                return ProviderResult(
                    output=content,
                    latency_ms=(time.perf_counter() - started) * 1000,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    cost_usd=cost,
                    retry_count=retries,
                    rate_limit_count=rate_limits,
                )
            except urllib.error.HTTPError as exc:
                transient = exc.code == 429 or 500 <= exc.code < 600
                if exc.code == 429:
                    rate_limits += 1
                if transient and attempt < self.config.max_retries:
                    retries += 1
                    self._sleeper(self.config.retry_delay_seconds)
                    continue
                return ProviderResult(
                    output=None,
                    latency_ms=(time.perf_counter() - started) * 1000,
                    retry_count=retries,
                    rate_limit_count=rate_limits,
                    error=f"provider HTTP {exc.code}",
                    failure_class="transient_exhausted" if transient else "permanent",
                )
            except (OSError, ValueError, KeyError, TypeError) as exc:
                if attempt < self.config.max_retries:
                    retries += 1
                    self._sleeper(self.config.retry_delay_seconds)
                    continue
                return ProviderResult(
                    output=None,
                    latency_ms=(time.perf_counter() - started) * 1000,
                    retry_count=retries,
                    rate_limit_count=rate_limits,
                    error=f"provider response error: {type(exc).__name__}",
                    failure_class="transient_exhausted",
                )

        raise ProviderError("unreachable provider retry state")


def adapter_from_environment(prefix: str, default_model: str = "") -> OpenAICompatibleAdapter:
    base_url = os.getenv(f"{prefix}_BASE_URL")
    api_key = os.getenv(f"{prefix}_API_KEY")
    model = os.getenv(f"{prefix}_MODEL") or default_model
    if not base_url or not api_key or not model:
        raise ValueError(f"{prefix}_BASE_URL, {prefix}_API_KEY, and {prefix}_MODEL are required")

    def optional_float(name: str) -> float | None:
        value = os.getenv(f"{prefix}_{name}")
        return float(value) if value else None

    return OpenAICompatibleAdapter(
        OpenAICompatibleConfig(
            base_url=base_url,
            api_key=api_key,
            model=model,
            max_retries=int(os.getenv(f"{prefix}_MAX_RETRIES", "2")),
            input_cost_per_million=optional_float("INPUT_COST_PER_MILLION"),
            output_cost_per_million=optional_float("OUTPUT_COST_PER_MILLION"),
        )
    )
