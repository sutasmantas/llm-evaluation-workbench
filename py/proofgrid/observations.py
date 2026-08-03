from __future__ import annotations

import json
import math
import statistics
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from autoevals import Score
from jsonschema import Draft202012Validator

from .runner import canonical_hash


MAX_BUNDLE_BYTES = 10_000_000
MAX_OBSERVATIONS = 500
ANSWER_DIMENSIONS = (
    "addresses_question",
    "uses_approved_context",
    "no_unsupported_claim",
    "concise_for_realtime",
    "usable_structure",
    "clarifies_when_needed",
)
DEFAULT_ANSWER_PROMOTION = {
    "min_case_pass_rate": 0.8,
    "max_unsupported_claim_failures": 0,
    "max_provider_failures": 0,
    "max_unresolved_reviews": 0,
    "max_first_useful_p95_ms": 3000,
}

_BUNDLE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["schema", "capturedAt", "candidate", "capture", "observations", "privacy"],
    "properties": {
        "schema": {"const": "contextsidecar.answer-observations.v1"},
        "capturedAt": {"type": "string", "minLength": 1},
        "environment": {"type": "object"},
        "candidate": {
            "type": "object",
            "additionalProperties": False,
            "required": ["id", "provider", "model", "endpoint"],
            "properties": {
                "id": {"type": "string", "minLength": 1},
                "provider": {"type": "string", "minLength": 1},
                "model": {"type": "string", "minLength": 1},
                "endpoint": {"type": "string", "minLength": 1},
            },
        },
        "capture": {
            "type": "object",
            "required": ["casesSha256", "replayContractSha256", "contextPacksSha256", "caseIds"],
            "properties": {
                "casesSha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                "replayContractSha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                "contextPacksSha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                "caseIds": {"type": "array", "minItems": 1, "uniqueItems": True},
            },
        },
        "observations": {"type": "array", "minItems": 1, "maxItems": MAX_OBSERVATIONS},
        "privacy": {
            "type": "object",
            "required": ["apiKeyPersisted", "fullContextPersisted"],
            "properties": {
                "apiKeyPersisted": {"const": False},
                "fullContextPersisted": {"const": False},
            },
        },
    },
}


class ObservationImportError(ValueError):
    pass


def _finite_number(value: Any, field: str, *, nullable: bool = False) -> float | None:
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ObservationImportError(f"{field} must be a non-negative finite number")
    return float(value)


def _validate_observation(item: Any, index: int) -> None:
    if not isinstance(item, dict):
        raise ObservationImportError(f"observation {index} must be an object")
    required = {
        "caseId",
        "split",
        "category",
        "inputMode",
        "input",
        "contextIds",
        "expected",
        "stream",
        "outcome",
        "output",
        "timing",
        "usage",
        "failure",
    }
    missing = sorted(required - item.keys())
    if missing:
        raise ObservationImportError(f"observation {index} is missing: {', '.join(missing)}")
    if not isinstance(item["caseId"], str) or not item["caseId"].strip():
        raise ObservationImportError(f"observation {index} requires caseId")
    if item["split"] not in {"development", "held_out"}:
        raise ObservationImportError(f"{item['caseId']} has unsupported split")
    if item["inputMode"] not in {"audio", "typed", "screenshot"}:
        raise ObservationImportError(f"{item['caseId']} has unsupported inputMode")
    if not isinstance(item["input"], str) or not item["input"].strip():
        raise ObservationImportError(f"{item['caseId']} requires input")
    if not isinstance(item["contextIds"], list) or not all(isinstance(value, str) for value in item["contextIds"]):
        raise ObservationImportError(f"{item['caseId']} contextIds must be strings")
    expected = item["expected"]
    if not isinstance(expected, dict):
        raise ObservationImportError(f"{item['caseId']} expected must be an object")
    for field in ("points", "mustNotClaim"):
        if not isinstance(expected.get(field), list) or not all(isinstance(value, str) for value in expected[field]):
            raise ObservationImportError(f"{item['caseId']} expected.{field} must contain strings")
    if not isinstance(expected.get("answerFormat"), str) or not expected["answerFormat"].strip():
        raise ObservationImportError(f"{item['caseId']} expected.answerFormat is required")
    stream = item["stream"]
    if not isinstance(stream, list):
        raise ObservationImportError(f"{item['caseId']} stream must be an array")
    previous_ms = -1.0
    cumulative = 0
    for stream_index, delta in enumerate(stream):
        if not isinstance(delta, dict) or delta.get("index") != stream_index or not isinstance(delta.get("text"), str):
            raise ObservationImportError(f"{item['caseId']} stream indexes must be contiguous")
        elapsed = _finite_number(delta.get("elapsedMs"), f"{item['caseId']} stream elapsedMs")
        if elapsed < previous_ms:
            raise ObservationImportError(f"{item['caseId']} stream elapsedMs must be monotonic")
        previous_ms = elapsed
        cumulative += len(delta["text"])
        if delta.get("cumulativeChars") != cumulative:
            raise ObservationImportError(f"{item['caseId']} stream cumulativeChars is inconsistent")
    timing = item["timing"]
    if not isinstance(timing, dict):
        raise ObservationImportError(f"{item['caseId']} timing must be an object")
    first_delta = _finite_number(timing.get("firstDeltaMs"), f"{item['caseId']} firstDeltaMs", nullable=True)
    completed = _finite_number(timing.get("completedMs"), f"{item['caseId']} completedMs")
    if stream and first_delta != float(stream[0]["elapsedMs"]):
        raise ObservationImportError(f"{item['caseId']} firstDeltaMs does not match the first stream delta")
    if not stream and first_delta is not None:
        raise ObservationImportError(f"{item['caseId']} firstDeltaMs requires a stream delta")
    if first_delta is not None and completed < first_delta:
        raise ObservationImportError(f"{item['caseId']} completion precedes its first delta")
    if item["outcome"] == "success":
        if not isinstance(item["output"], str) or item["failure"] is not None or item["usage"] is None:
            raise ObservationImportError(f"{item['caseId']} has an inconsistent successful outcome")
        if not stream or not item["output"]:
            raise ObservationImportError(f"{item['caseId']} successful outcome requires streamed output")
        if item["output"] != "".join(delta["text"] for delta in stream):
            raise ObservationImportError(f"{item['caseId']} output does not match its stream")
        usage = item["usage"]
        if not isinstance(usage, dict):
            raise ObservationImportError(f"{item['caseId']} usage must be an object")
        for field in (
            "promptTokens",
            "completionTokens",
            "totalTokens",
            "promptCacheHitTokens",
            "promptCacheMissTokens",
        ):
            _finite_number(usage.get(field), f"{item['caseId']} usage.{field}", nullable=True)
        if usage.get("promptTokens") is not None and usage.get("completionTokens") is not None:
            expected_total = usage["promptTokens"] + usage["completionTokens"]
            if usage.get("totalTokens") != expected_total:
                raise ObservationImportError(f"{item['caseId']} usage.totalTokens is inconsistent")
    elif item["outcome"] == "error":
        if item["output"] is not None or not isinstance(item["failure"], dict):
            raise ObservationImportError(f"{item['caseId']} has an inconsistent error outcome")
        if (
            not isinstance(item["failure"].get("message"), str)
            or not item["failure"]["message"].strip()
            or not isinstance(item["failure"].get("retryable"), bool)
        ):
            raise ObservationImportError(f"{item['caseId']} failure must contain message and retryable")
    else:
        raise ObservationImportError(f"{item['caseId']} has unsupported outcome")


def parse_observation_bundle(content: str) -> dict[str, Any]:
    if len(content.encode("utf-8")) > MAX_BUNDLE_BYTES:
        raise ObservationImportError(f"observation bundle exceeds {MAX_BUNDLE_BYTES} bytes")
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ObservationImportError("observation bundle is invalid JSON") from exc
    errors = sorted(Draft202012Validator(_BUNDLE_SCHEMA).iter_errors(payload), key=lambda error: list(error.path))
    if errors:
        raise ObservationImportError(f"observation bundle schema error: {errors[0].message}")
    observations = payload["observations"]
    for index, item in enumerate(observations, start=1):
        _validate_observation(item, index)
    observed_ids = [item["caseId"] for item in observations]
    if len(observed_ids) != len(set(observed_ids)):
        raise ObservationImportError("observation caseId values must be unique")
    if observed_ids != payload["capture"]["caseIds"]:
        raise ObservationImportError("capture caseIds must match observation order")
    endpoint = urlsplit(payload["candidate"]["endpoint"])
    if endpoint.scheme not in {"http", "https"} or not endpoint.netloc:
        raise ObservationImportError("candidate endpoint must be an absolute HTTP(S) URL")
    if endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
        raise ObservationImportError("candidate endpoint must not contain credentials, query, or fragment")
    return payload


def load_observation_bundle(path: str | Path) -> dict[str, Any]:
    candidate = Path(path).resolve()
    if candidate.suffix.lower() != ".json" or not candidate.is_file():
        raise ObservationImportError("observation bundle must be an existing .json file")
    if candidate.stat().st_size > MAX_BUNDLE_BYTES:
        raise ObservationImportError(f"observation bundle exceeds {MAX_BUNDLE_BYTES} bytes")
    return parse_observation_bundle(candidate.read_text(encoding="utf-8-sig"))


def _pricing_for(candidate_id: str, pricing: dict[str, Any] | None) -> dict[str, Any] | None:
    if pricing is None:
        return None
    row = pricing.get(candidate_id)
    if not isinstance(row, dict):
        raise ObservationImportError(f"pricing is missing candidate {candidate_id}")
    input_rate = _finite_number(row.get("input_per_million_usd"), f"{candidate_id} input price")
    output_rate = _finite_number(row.get("output_per_million_usd"), f"{candidate_id} output price")
    source = row.get("source")
    if not isinstance(source, str) or not source.strip():
        raise ObservationImportError(f"pricing source is required for {candidate_id}")
    return {"input": input_rate, "output": output_rate, "source": source.strip()}


def _cost(usage: dict[str, Any] | None, pricing: dict[str, Any] | None) -> float | None:
    if usage is None or pricing is None:
        return None
    prompt = usage.get("promptTokens")
    completion = usage.get("completionTokens")
    if prompt is None or completion is None:
        return None
    return (prompt * pricing["input"] + completion * pricing["output"]) / 1_000_000


def _percentile(values: list[float], percentile: int) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.ceil(percentile / 100 * len(ordered)) - 1]


def summarize_answer_candidate(rows: list[dict[str, Any]], promotion: dict[str, Any]) -> dict[str, Any]:
    reviewed = [row for row in rows if row.get("human_score") is not None]
    passing = [row for row in reviewed if row.get("human_pass")]
    first_useful = [row["first_useful_ms"] for row in reviewed if row.get("first_useful_ms") is not None]
    completion = [row["latency_ms"] for row in rows if row.get("failure_class") is None]
    unresolved = sum(bool(row["needs_review"]) for row in rows)
    provider_failures = sum(row.get("failure_class") is not None for row in rows)
    unsupported = sum(bool(row.get("unsupported_claim_failure")) for row in reviewed)
    cost_values = [row.get("cost_usd") for row in rows if row.get("failure_class") is None]
    total_cost = sum(cost_values) if cost_values and all(value is not None for value in cost_values) else None
    pass_rate = len(passing) / len(rows)
    first_useful_p95 = _percentile(first_useful, 95)
    gate_checks = {
        "case_pass_rate": pass_rate >= promotion["min_case_pass_rate"],
        "unsupported_claim_failures": unsupported <= promotion["max_unsupported_claim_failures"],
        "provider_failures": provider_failures <= promotion["max_provider_failures"],
        "unresolved_reviews": unresolved <= promotion["max_unresolved_reviews"],
        "first_useful_p95_ms": first_useful_p95 is not None
        and first_useful_p95 <= promotion["max_first_useful_p95_ms"],
    }
    return {
        "evaluated_cases": len(rows),
        "reviewed_cases": len(reviewed),
        "case_pass_rate": round(pass_rate, 6),
        "unsupported_claim_failures": unsupported,
        "provider_failures": provider_failures,
        "unresolved_reviews": unresolved,
        "first_delta_p50_ms": _percentile(
            [row["first_delta_ms"] for row in rows if row.get("first_delta_ms") is not None], 50
        ),
        "first_delta_p95_ms": _percentile(
            [row["first_delta_ms"] for row in rows if row.get("first_delta_ms") is not None], 95
        ),
        "first_useful_p50_ms": _percentile(first_useful, 50),
        "first_useful_p95_ms": first_useful_p95,
        "completion_p50_ms": _percentile(completion, 50),
        "completion_p95_ms": _percentile(completion, 95),
        "median_latency_ms": statistics.median(completion) if completion else None,
        "total_cost_usd": round(total_cost, 8) if total_cost is not None else None,
        "gate_checks": gate_checks,
        "promoted": all(gate_checks.values()),
    }


def recompute_answer_decision(result: dict[str, Any]) -> None:
    for candidate in result["candidates"]:
        candidate["summary"] = summarize_answer_candidate(candidate["rows"], result["promotion_rule"])
    promoted = [candidate for candidate in result["candidates"] if candidate["summary"]["promoted"]]
    comparable = len(result["candidates"]) >= 2
    winner = None
    if comparable and promoted:
        winner = min(
            promoted,
            key=lambda candidate: (
                candidate["summary"]["total_cost_usd"]
                if candidate["summary"]["total_cost_usd"] is not None
                else math.inf,
                candidate["summary"]["first_useful_p95_ms"],
                candidate["summary"]["completion_p95_ms"],
                candidate["candidate_id"],
            ),
        )["candidate_id"]
    result["decision"] = {
        "comparable_candidates": comparable,
        "promoted_candidates": [candidate["candidate_id"] for candidate in promoted],
        "winner": winner,
        "winner_basis": "pass frozen human/latency/failure gates, then cost, first-useful p95, completion p95, candidate id",
        "provider_superiority_claim_allowed": False,
        "scope": "same ContextSidecar corpus and capture contract only",
    }


def import_observation_bundles(
    bundles: list[dict[str, Any]],
    *,
    pricing: dict[str, Any] | None = None,
    promotion: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not bundles:
        raise ObservationImportError("at least one observation bundle is required")
    candidate_ids = [bundle["candidate"]["id"] for bundle in bundles]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ObservationImportError("candidate ids must be unique")
    reference = bundles[0]
    comparison_keys = ("casesSha256", "replayContractSha256", "contextPacksSha256", "caseIds")
    for bundle in bundles[1:]:
        if any(bundle["capture"][key] != reference["capture"][key] for key in comparison_keys):
            raise ObservationImportError("candidate bundles do not share the same frozen capture inputs")
    promotion_rule = {**DEFAULT_ANSWER_PROMOTION, **(promotion or {})}
    unknown_promotion = set(promotion_rule) - set(DEFAULT_ANSWER_PROMOTION)
    if unknown_promotion:
        raise ObservationImportError(f"unknown answer promotion fields: {', '.join(sorted(unknown_promotion))}")
    for key, value in promotion_rule.items():
        _finite_number(value, f"promotion.{key}")
    if promotion_rule["min_case_pass_rate"] > 1:
        raise ObservationImportError("promotion.min_case_pass_rate must be at most 1")

    def case_contract(bundle: dict[str, Any]) -> list[dict[str, Any]]:
        fields = ("caseId", "split", "category", "inputMode", "input", "contextIds", "expected")
        return [{field: item[field] for field in fields} for item in bundle["observations"]]

    reference_cases = case_contract(reference)
    for bundle in bundles[1:]:
        if case_contract(bundle) != reference_cases:
            raise ObservationImportError("candidate bundles do not contain identical case contracts")

    cases = [
        {
            "case_id": item["caseId"],
            "split": "heldout" if item["split"] == "held_out" else "train",
            "category": item["category"],
            "input": item["input"],
            "expected": item["expected"],
            "tags": [item["inputMode"], *item["contextIds"]],
        }
        for item in reference["observations"]
    ]
    result: dict[str, Any] = {
        "kind": "answer_observation_comparison",
        "run_id": f"run_{uuid.uuid4().hex[:12]}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "suite_hash": canonical_hash({key: reference["capture"][key] for key in comparison_keys}),
        "schema_hash": canonical_hash({"schema": reference["schema"]}),
        "promotion_hash": canonical_hash(promotion_rule),
        "promotion_rule": promotion_rule,
        "schema": {"id": reference["schema"]},
        "cases": cases,
        "candidates": [],
        "source": {
            "schema": reference["schema"],
            "capture": {key: reference["capture"][key] for key in comparison_keys},
        },
    }
    for bundle in bundles:
        candidate = bundle["candidate"]
        candidate_pricing = _pricing_for(candidate["id"], pricing)
        rows = []
        for item in bundle["observations"]:
            usage = item["usage"]
            failure_class = None
            error = None
            if item["outcome"] == "error":
                failure_class = "transient_exhausted" if item["failure"].get("retryable") else "permanent"
                error = item["failure"]["message"]
            rows.append(
                {
                    "case_id": item["caseId"],
                    "split": "heldout" if item["split"] == "held_out" else "train",
                    "category": item["category"],
                    "expected": item["expected"],
                    "output": item["output"],
                    "stream": item["stream"],
                    "first_delta_ms": item["timing"]["firstDeltaMs"],
                    "first_useful_ms": None,
                    "latency_ms": item["timing"]["completedMs"],
                    "prompt_tokens": usage.get("promptTokens") if usage else None,
                    "completion_tokens": usage.get("completionTokens") if usage else None,
                    "total_tokens": usage.get("totalTokens") if usage else None,
                    "cost_usd": _cost(usage, candidate_pricing),
                    "pricing_source": candidate_pricing["source"] if candidate_pricing else None,
                    "retry_count": 0,
                    "rate_limit_count": 0,
                    "error": error,
                    "failure_class": failure_class,
                    "human_score": None,
                    "human_pass": None,
                    "unsupported_claim_failure": None,
                    "review": None,
                    "needs_review": True,
                    "review_reason": error or "human_answer_review_required",
                }
            )
        result["candidates"].append(
            {
                "candidate_id": candidate["id"],
                "label": candidate["id"],
                "provider": candidate["provider"],
                "model": candidate["model"],
                "response_mode": "contextsidecar-stream",
                "prompt_hash": bundle["capture"]["contextPacksSha256"],
                "config_hash": canonical_hash(
                    {
                        "provider": candidate["provider"],
                        "model": candidate["model"],
                        "endpoint": candidate["endpoint"],
                        "capture": bundle["capture"],
                    }
                ),
                "capture": {
                    "captured_at": bundle["capturedAt"],
                    "environment": bundle.get("environment", {}),
                    "pricing": candidate_pricing,
                },
                "rows": rows,
            }
        )
    recompute_answer_decision(result)
    return result


def score_answer_review(
    row: dict[str, Any],
    *,
    reviewer: str,
    first_useful_delta_index: int | None,
    scores: dict[str, Any],
    note: str = "",
) -> dict[str, Any]:
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError("reviewer is required")
    if set(scores) != set(ANSWER_DIMENSIONS):
        raise ValueError("answer review scores must contain exactly the six rubric dimensions")
    values = []
    for dimension in ANSWER_DIMENSIONS:
        value = scores[dimension]
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 2:
            raise ValueError(f"{dimension} must be an integer from 0 to 2")
        values.append(value)
    first_useful_ms = None
    if row["failure_class"] is None:
        if (
            isinstance(first_useful_delta_index, bool)
            or not isinstance(first_useful_delta_index, int)
            or first_useful_delta_index < 0
            or first_useful_delta_index >= len(row["stream"])
        ):
            raise ValueError("first_useful_delta_index must select an observed stream delta")
        first_useful_ms = row["stream"][first_useful_delta_index]["elapsedMs"]
    elif first_useful_delta_index is not None:
        raise ValueError("failed provider observations cannot select a first-useful delta")
    total = sum(values)
    passed = total >= 9 and 0 not in values and row["failure_class"] is None
    score = Score(
        name="AnswerHumanRubric",
        score=total / 12,
        metadata={
            "reviewer": reviewer.strip(),
            "scores": scores,
            "total": total,
            "pass": passed,
            "first_useful_delta_index": first_useful_delta_index,
            "first_useful_ms": first_useful_ms,
            "note": note,
        },
    )
    return score.as_dict()
