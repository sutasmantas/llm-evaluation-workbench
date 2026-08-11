from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from inspect_ai.log import EvalLog, read_eval_log
from inspect_ai.model import ModelOutput
from inspect_ai.scorer import Score, mean, scorer, stderr
from inspect_ai.solver import Generate, TaskState, solver
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from .runner import canonical_hash


INSPECT_AI_REVISION = "cb00efcd12dfbf3e44f486648e05e54f1337fe9a"
INSPECT_AI_VERSION = "0.3.253.dev7+gcb00efcd1"
CONTRACT_VERSION = "proofgrid.inspect-json-schema.v1"
SCORER_NAME = "json_schema_contract"


@solver
def observed_json() -> Any:
    """Emit a sample's precomputed observation without invoking a model."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        if "observed" not in state.metadata:
            raise ValueError("sample metadata must contain observed")
        state.output = ModelOutput.from_content(
            model="proofgrid/observed-json",
            content=json.dumps(state.metadata["observed"], ensure_ascii=False, sort_keys=True),
        )
        return state

    return solve


@scorer(metrics=[mean(), stderr()])
def json_schema_contract() -> Any:
    """Validate executable task output against the sample's JSON Schema target."""

    async def score(state: TaskState, target: Any) -> Score:
        try:
            observed = json.loads(state.output.completion)
        except json.JSONDecodeError as exc:
            return Score(
                value=0,
                explanation=f"output is not JSON: {exc.msg}",
                metadata={"failure_class": "invalid_output_json"},
            )
        try:
            schema = json.loads(target.text)
            Draft202012Validator.check_schema(schema)
        except (json.JSONDecodeError, SchemaError) as exc:
            return Score(
                value=0,
                explanation=f"oracle is not a valid JSON Schema: {exc}",
                metadata={"failure_class": "invalid_oracle"},
            )

        errors = sorted(
            Draft202012Validator(schema).iter_errors(observed),
            key=lambda error: (list(error.absolute_path), error.message),
        )
        if not errors:
            return Score(
                value=1,
                explanation="output satisfies the frozen JSON Schema oracle",
                metadata={"failure_class": None, "error_count": 0},
            )
        details = [
            {
                "path": "/".join(str(part) for part in error.absolute_path) or "$",
                "message": error.message,
            }
            for error in errors[:10]
        ]
        return Score(
            value=0,
            explanation="; ".join(f"{item['path']}: {item['message']}" for item in details),
            metadata={
                "failure_class": "contract_mismatch",
                "error_count": len(errors),
                "errors": details,
            },
        )

    return score


def _numeric_score(value: Any, case_id: str) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    raise ValueError(f"sample {case_id}: scorer value must be numeric")


def import_inspect_log(
    log_file: str | Path | EvalLog,
    *,
    scorer_name: str = SCORER_NAME,
    minimum_score: float = 1.0,
) -> dict[str, Any]:
    """Normalize one pinned Inspect log into ProofGrid's result contract."""

    if not 0 <= minimum_score <= 1:
        raise ValueError("minimum_score must be between zero and one")
    log = log_file if isinstance(log_file, EvalLog) else read_eval_log(log_file)
    if log.status != "success":
        raise ValueError(f"Inspect log status must be success, got {log.status}")
    if not log.samples:
        raise ValueError("Inspect log must include samples")
    metadata = dict(log.eval.metadata or {})
    if metadata.get("proofgrid_contract") != CONTRACT_VERSION:
        raise ValueError(f"Inspect task must declare proofgrid_contract={CONTRACT_VERSION}")
    if metadata.get("inspect_revision") != INSPECT_AI_REVISION:
        raise ValueError(f"Inspect task must declare inspect_revision={INSPECT_AI_REVISION}")
    packages = dict(log.eval.packages or {})
    if packages.get("inspect_ai") != INSPECT_AI_VERSION:
        raise ValueError(f"Inspect log must use inspect_ai {INSPECT_AI_VERSION}")
    if log.eval.task_version is None or not str(log.eval.task_version).strip():
        raise ValueError("Inspect task must declare a non-empty task_version")
    source_log = Path(str(log.location)) if log.location else None
    if source_log and source_log.is_file():
        source_log_name = source_log.name
        source_log_sha256 = hashlib.sha256(source_log.read_bytes()).hexdigest()
    else:
        source_log_name = "in-memory"
        source_log_sha256 = canonical_hash(log.model_dump(mode="json"))

    rows: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []
    case_ids: set[str] = set()
    for sample in log.samples:
        case_id = str(sample.id)
        if case_id in case_ids:
            raise ValueError(f"duplicate Inspect sample id: {case_id}")
        case_ids.add(case_id)
        scores = dict(sample.scores or {})
        if scorer_name not in scores:
            raise ValueError(f"sample {case_id}: missing scorer {scorer_name}")
        imported_score = scores[scorer_name]
        score_value = _numeric_score(imported_score.value, case_id)
        error = sample.error.model_dump(mode="json") if sample.error else None
        passed = error is None and score_value >= minimum_score
        sample_metadata = dict(sample.metadata or {})
        output = sample.output.completion if sample.output else None
        row = {
            "case_id": case_id,
            "split": str(sample_metadata.get("split") or "heldout"),
            "category": str(sample_metadata.get("category") or "uncategorized"),
            "output": output,
            "expected": sample.target,
            "schema_score": score_value,
            "task_score": score_value,
            "exact_score": None,
            "latency_ms": round(float(sample.working_time or sample.total_time or 0) * 1000, 3),
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "cost_usd": None,
            "retry_count": int(sample.error_retries or 0),
            "rate_limit_count": 0,
            "failure_class": "inspect_sample_error" if error else (imported_score.metadata or {}).get("failure_class"),
            "error": error,
            "score_explanation": imported_score.explanation,
            "score_metadata": imported_score.metadata,
            "needs_review": False,
            "review_reason": None if passed else "executable_contract_failed",
            "passed": passed,
        }
        rows.append(row)
        cases.append(
            {
                "case_id": case_id,
                "split": row["split"],
                "category": row["category"],
                "input": sample.input,
                "expected": sample.target,
            }
        )

    passed_cases = sum(row["passed"] for row in rows)
    pass_rate = passed_cases / len(rows)
    promoted = passed_cases == len(rows)
    summary = {
        "evaluated_cases": len(rows),
        "passed_cases": passed_cases,
        "pass_rate": round(pass_rate, 6),
        "minimum_score": minimum_score,
        "sample_errors": sum(row["error"] is not None for row in rows),
        "gate_checks": {
            "all_samples_scored": True,
            "minimum_score": promoted,
            "sample_errors": all(row["error"] is None for row in rows),
        },
        "promoted": promoted,
    }
    task_id = str(log.eval.task)
    suite_manifest = {
        "contract": CONTRACT_VERSION,
        "inspect_revision": INSPECT_AI_REVISION,
        "task": task_id,
        "task_version": str(log.eval.task_version),
        "cases": cases,
    }
    candidate = {
        "candidate_id": task_id,
        "label": str(log.eval.task_display_name or task_id),
        "provider": "inspect-ai",
        "model": str(log.eval.model),
        "response_mode": "executable-agent",
        "prompt_hash": canonical_hash({"solver": log.eval.solver, "task": task_id}),
        "config_hash": canonical_hash(
            {
                "task_version": str(log.eval.task_version),
                "scorer": scorer_name,
                "minimum_score": minimum_score,
                "metadata": metadata,
            }
        ),
        "rows": rows,
        "summary": summary,
    }
    return {
        "kind": "inspect_executable_evaluation",
        "run_id": f"inspect_{log.eval.eval_id}",
        "created_at": str(log.eval.created),
        "suite_hash": canonical_hash(suite_manifest),
        "promotion_hash": canonical_hash({"scorer": scorer_name, "minimum_score": minimum_score}),
        "promotion_rule": {"scorer": scorer_name, "minimum_score": minimum_score},
        "source": {
            "framework": "inspect-ai",
            "framework_version": INSPECT_AI_VERSION,
            "framework_revision": INSPECT_AI_REVISION,
            "log_name": source_log_name,
            "log_sha256": source_log_sha256,
            "eval_id": str(log.eval.eval_id),
            "task_version": str(log.eval.task_version),
        },
        "cases": cases,
        "candidates": [candidate],
        "decision": {
            "promoted_candidates": [task_id] if promoted else [],
            "winner": task_id if promoted else None,
            "winner_basis": "all executable samples satisfy the frozen JSON Schema oracle",
            "provider_superiority_claim_allowed": False,
            "scope": "pinned executable task and frozen consumer-local schemas only",
        },
    }
