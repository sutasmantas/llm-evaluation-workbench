from __future__ import annotations

import csv
import hashlib
import io
import json
import statistics
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from autoevals import ExactMatch, JSONDiff, ValidJSON

from .models import Candidate, EvalCase
from .providers import DeterministicAdapter, OpenAICompatibleAdapter, adapter_from_environment


MAX_IMPORT_BYTES = 1_000_000
MAX_CASES = 500


class CaseImportError(ValueError):
    pass


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _case_from_mapping(row: dict[str, Any], index: int) -> EvalCase:
    case_id = str(row.get("case_id") or row.get("id") or "").strip()
    source = row.get("input")
    expected = row.get("expected")
    if isinstance(expected, str):
        try:
            expected = json.loads(expected)
        except json.JSONDecodeError as exc:
            raise CaseImportError(f"row {index}: expected must be JSON") from exc
    if not case_id or not isinstance(source, str) or not isinstance(expected, dict):
        raise CaseImportError(f"row {index}: case_id, string input, and object expected are required")
    split = str(row.get("split") or "train").strip().lower()
    if split not in {"train", "heldout"}:
        raise CaseImportError(f"row {index}: split must be train or heldout")
    tags = row.get("tags") or []
    if isinstance(tags, str):
        tags = [part.strip() for part in tags.split("|") if part.strip()]
    return EvalCase(
        case_id=case_id,
        split=split,
        category=str(row.get("category") or "uncategorized"),
        input=source,
        expected=expected,
        tags=tuple(str(tag) for tag in tags),
    )


def parse_cases(content: str, format_name: str) -> list[EvalCase]:
    if len(content.encode("utf-8")) > MAX_IMPORT_BYTES:
        raise CaseImportError(f"case import exceeds {MAX_IMPORT_BYTES} bytes")
    normalized = format_name.lower().lstrip(".")
    rows: Iterable[dict[str, Any]]
    if normalized == "jsonl":
        parsed_rows = []
        for line_number, line in enumerate(content.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise CaseImportError(f"line {line_number}: invalid JSON") from exc
            if not isinstance(item, dict):
                raise CaseImportError(f"line {line_number}: each JSONL row must be an object")
            parsed_rows.append(item)
        rows = parsed_rows
    elif normalized == "csv":
        rows = csv.DictReader(io.StringIO(content))
    else:
        raise CaseImportError("case format must be csv or jsonl")

    cases = [_case_from_mapping(dict(row), index) for index, row in enumerate(rows, start=1)]
    if not cases:
        raise CaseImportError("case import is empty")
    if len(cases) > MAX_CASES:
        raise CaseImportError(f"case import exceeds {MAX_CASES} cases")
    ids = [case.case_id for case in cases]
    if len(ids) != len(set(ids)):
        raise CaseImportError("case_id values must be unique")
    if not any(case.split == "heldout" for case in cases):
        raise CaseImportError("at least one heldout case is required")
    return cases


def load_cases(path: str | Path) -> list[EvalCase]:
    candidate = Path(path).resolve()
    if candidate.suffix.lower() not in {".jsonl", ".csv"}:
        raise CaseImportError("case file must use .jsonl or .csv")
    if not candidate.is_file():
        raise CaseImportError(f"case file not found: {candidate.name}")
    if candidate.stat().st_size > MAX_IMPORT_BYTES:
        raise CaseImportError(f"case import exceeds {MAX_IMPORT_BYTES} bytes")
    return parse_cases(candidate.read_text(encoding="utf-8-sig"), candidate.suffix)


def load_candidates(path: str | Path) -> list[Candidate]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = payload.get("candidates") if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or not rows:
        raise ValueError("candidate file must contain a non-empty candidates list")
    candidates = []
    for row in rows:
        candidates.append(
            Candidate(
                candidate_id=row["candidate_id"],
                label=row["label"],
                prompt=row["prompt"],
                provider=row["provider"],
                model=row["model"],
                response_mode=row["response_mode"],
                max_retries=int(row.get("max_retries", 0)),
                metadata=dict(row.get("metadata") or {}),
            )
        )
    return candidates


def adapters_for_candidates(candidates: list[Candidate]) -> dict[str, Any]:
    adapters: dict[str, Any] = {"deterministic-local": DeterministicAdapter()}
    if any(candidate.provider == "openai-compatible" for candidate in candidates):
        default_model = next(candidate.model for candidate in candidates if candidate.provider == "openai-compatible")
        adapters["openai-compatible"] = adapter_from_environment("PROOFGRID_PROVIDER", default_model)
    return adapters


def _evaluate_output(output: str | None, expected: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    if output is None:
        return {"schema_score": 0.0, "task_score": 0.0, "exact_score": 0.0, "parsed_output": None}
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError:
        parsed = None
    # AutoEvals ValidJSON names the Scorer "expected" position `schema`, so the
    # schema must be passed positionally; using schema= raises a duplicate-value
    # TypeError in the inherited Scorer.eval wrapper.
    schema_score = float(ValidJSON().eval(output, schema).score or 0)
    task_score = float(JSONDiff().eval(output, expected).score or 0)
    exact_output = json.dumps(parsed, ensure_ascii=False, sort_keys=True) if parsed is not None else output
    exact_expected = json.dumps(expected, ensure_ascii=False, sort_keys=True)
    exact_score = float(ExactMatch().eval(exact_output, exact_expected).score or 0)
    return {
        "schema_score": schema_score,
        "task_score": task_score,
        "exact_score": exact_score,
        "parsed_output": parsed,
    }


def summarize_candidate(rows: list[dict[str, Any]], promotion: dict[str, Any]) -> dict[str, Any]:
    heldout = [row for row in rows if row["split"] == "heldout"]
    scope = heldout or rows
    count = len(scope)
    schema_pass_rate = sum(row["schema_score"] >= 1 for row in scope) / count
    exact_pass_rate = sum(row["exact_score"] >= 1 for row in scope) / count
    mean_task_score = sum(row["task_score"] for row in scope) / count
    unresolved_reviews = sum(row["needs_review"] for row in scope)
    permanent_failures = sum(row["failure_class"] == "permanent" for row in scope)
    exhausted_failures = sum(row["failure_class"] == "transient_exhausted" for row in scope)
    latencies = [row["latency_ms"] for row in scope]
    total_cost = sum(row["cost_usd"] or 0 for row in scope)
    gate_checks = {
        "schema_pass_rate": schema_pass_rate >= promotion["min_schema_pass_rate"],
        "exact_pass_rate": exact_pass_rate >= promotion["min_exact_pass_rate"],
        "mean_task_score": mean_task_score >= promotion["min_mean_task_score"],
        "unresolved_reviews": unresolved_reviews <= promotion["max_unresolved_reviews"],
        "provider_failures": permanent_failures == 0 and exhausted_failures == 0,
    }
    return {
        "evaluated_cases": count,
        "schema_pass_rate": round(schema_pass_rate, 6),
        "exact_pass_rate": round(exact_pass_rate, 6),
        "mean_task_score": round(mean_task_score, 6),
        "median_latency_ms": round(statistics.median(latencies), 3),
        "total_cost_usd": round(total_cost, 8),
        "retry_count": sum(row["retry_count"] for row in scope),
        "rate_limit_count": sum(row["rate_limit_count"] for row in scope),
        "unresolved_reviews": unresolved_reviews,
        "permanent_failures": permanent_failures,
        "transient_exhausted_failures": exhausted_failures,
        "gate_checks": gate_checks,
        "promoted": all(gate_checks.values()),
    }


def choose_winner(candidates: list[dict[str, Any]]) -> str | None:
    promoted = [candidate for candidate in candidates if candidate["summary"]["promoted"]]
    if not promoted:
        return None
    winner = min(
        promoted,
        key=lambda candidate: (
            candidate["summary"]["total_cost_usd"],
            candidate["summary"]["retry_count"],
            candidate["summary"]["median_latency_ms"],
            candidate["candidate_id"],
        ),
    )
    return winner["candidate_id"]


def execute_suite(
    cases: list[EvalCase],
    candidates: list[Candidate],
    schema: dict[str, Any],
    promotion: dict[str, Any],
    adapters: dict[str, Any] | None = None,
    judge: OpenAICompatibleAdapter | None = None,
) -> dict[str, Any]:
    adapters = adapters or {"deterministic-local": DeterministicAdapter()}
    case_manifest = [
        {
            "case_id": case.case_id,
            "split": case.split,
            "category": case.category,
            "input": case.input,
            "expected": case.expected,
            "tags": list(case.tags),
        }
        for case in cases
    ]
    result: dict[str, Any] = {
        "run_id": f"run_{uuid.uuid4().hex[:12]}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "suite_hash": canonical_hash(case_manifest),
        "schema_hash": canonical_hash(schema),
        "promotion_hash": canonical_hash(promotion),
        "promotion_rule": promotion,
        "schema": schema,
        "cases": case_manifest,
        "candidates": [],
    }

    for candidate in candidates:
        adapter = adapters.get(candidate.provider)
        if adapter is None:
            raise ValueError(f"no adapter registered for provider {candidate.provider}")
        rows = []
        for case in cases:
            provider_result = adapter.generate(candidate, case)
            scored = _evaluate_output(provider_result.output, case.expected, schema)
            needs_review = bool(
                provider_result.error
                or scored["schema_score"] < 1
                or scored["exact_score"] < 1
                or scored["task_score"] < promotion["review_below_task_score"]
            )
            row = {
                "case_id": case.case_id,
                "split": case.split,
                "category": case.category,
                "expected": case.expected,
                "output": provider_result.output,
                **scored,
                **provider_result.as_dict(),
                "needs_review": needs_review,
                "review_reason": (
                    provider_result.error
                    or ("schema_invalid" if scored["schema_score"] < 1 else None)
                    or ("expected_output_mismatch" if scored["exact_score"] < 1 else None)
                ),
            }
            if judge is not None and provider_result.output is not None:
                judge_case = EvalCase(
                    case_id=case.case_id,
                    split=case.split,
                    category=case.category,
                    input=json.dumps(
                        {"input": case.input, "expected": case.expected, "output": provider_result.output}
                    ),
                    expected={"score": 1},
                )
                judge_candidate = Candidate(
                    candidate_id="optional-judge",
                    label="Optional rubric judge",
                    prompt=promotion.get("judge_rubric", "Score the output from 0 to 1 and explain."),
                    provider="openai-compatible",
                    model=promotion.get("judge_model", "judge"),
                    response_mode="judge",
                )
                judged = judge.generate(judge_candidate, judge_case)
                try:
                    judge_payload = json.loads(judged.output) if judged.output else {}
                    judge_score = float(judge_payload["score"])
                    if not 0 <= judge_score <= 1:
                        raise ValueError("judge score outside 0..1")
                    row["judge_score"] = judge_score
                    row["judge_reason"] = str(judge_payload.get("reason") or "")
                except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                    row["judge_score"] = None
                    row["judge_reason"] = judged.error or "judge returned an invalid score payload"
            rows.append(row)

        version = {
            "candidate_id": candidate.candidate_id,
            "label": candidate.label,
            "provider": candidate.provider,
            "model": candidate.model,
            "response_mode": candidate.response_mode,
            "prompt_hash": canonical_hash(candidate.prompt),
            "config_hash": canonical_hash(
                {
                    "provider": candidate.provider,
                    "model": candidate.model,
                    "response_mode": candidate.response_mode,
                    "max_retries": candidate.max_retries,
                    "metadata": candidate.metadata,
                }
            ),
        }
        result["candidates"].append({**version, "rows": rows, "summary": summarize_candidate(rows, promotion)})

    promoted = [candidate["candidate_id"] for candidate in result["candidates"] if candidate["summary"]["promoted"]]
    result["decision"] = {
        "promoted_candidates": promoted,
        "winner": choose_winner(result["candidates"]),
        "winner_basis": "pass frozen thresholds, then cost, retries, latency, candidate id",
        "provider_superiority_claim_allowed": False,
        "scope": "frozen deterministic fixture behavior only",
    }
    return result
