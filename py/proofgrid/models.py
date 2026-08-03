from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    split: str
    category: str
    input: str
    expected: dict[str, Any]
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    label: str
    prompt: str
    provider: str
    model: str
    response_mode: str
    max_retries: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderResult:
    output: str | None
    latency_ms: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost_usd: float | None = None
    retry_count: int = 0
    rate_limit_count: int = 0
    error: str | None = None
    failure_class: str | None = None
    judge_score: float | None = None
    judge_reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
