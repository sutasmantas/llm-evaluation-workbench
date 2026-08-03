from __future__ import annotations

import json
import urllib.error
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from .api import create_app
from .models import Candidate, EvalCase
from .providers import OpenAICompatibleAdapter, OpenAICompatibleConfig
from .runner import CaseImportError, canonical_hash, execute_suite, load_candidates, load_cases, parse_cases
from .store import RunStore


ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / "evals" / "proofgrid"


def load_experiment():
    return execute_suite(
        load_cases(SUITE / "cases.jsonl"),
        load_candidates(SUITE / "candidates.json"),
        json.loads((SUITE / "schema.json").read_text(encoding="utf-8")),
        json.loads((SUITE / "promotion.json").read_text(encoding="utf-8")),
    )


def test_jsonl_and_csv_import_share_the_case_contract():
    jsonl = (
        '{"case_id":"A","split":"heldout","category":"clean","input":"Name: A",' '"expected":{"contact_name":"A"}}\n'
    )
    csv_text = 'case_id,split,category,input,expected\nA,heldout,clean,Name: A,"{""contact_name"":""A""}"\n'
    jsonl_case = parse_cases(jsonl, "jsonl")[0]
    csv_case = parse_cases(csv_text, "csv")[0]
    assert jsonl_case == csv_case


@pytest.mark.parametrize(
    "content, message",
    [
        ('{"case_id":"A","split":"train","input":"x","expected":{}}', "heldout"),
        (
            '{"case_id":"A","split":"heldout","input":"x","expected":{}}\n'
            '{"case_id":"A","split":"heldout","input":"y","expected":{}}',
            "unique",
        ),
        ("not json", "invalid JSON"),
    ],
)
def test_case_import_refuses_invalid_batches(content, message):
    with pytest.raises(CaseImportError, match=message):
        parse_cases(content, "jsonl")


def test_frozen_experiment_promotes_only_repair_path():
    result = load_experiment()
    summaries = {item["candidate_id"]: item["summary"] for item in result["candidates"]}
    assert result["decision"]["winner"] == "repair"
    assert result["decision"]["provider_superiority_claim_allowed"] is False
    assert summaries["baseline"]["schema_pass_rate"] == 0
    assert summaries["structured"]["schema_pass_rate"] == 1
    assert summaries["structured"]["exact_pass_rate"] == pytest.approx(5 / 6, abs=1e-6)
    assert summaries["structured"]["unresolved_reviews"] == 1
    assert summaries["repair"]["exact_pass_rate"] == 1
    assert summaries["repair"]["retry_count"] == 1
    assert summaries["repair"]["rate_limit_count"] == 1


def test_run_versions_are_stable_while_run_identity_changes():
    first = load_experiment()
    second = load_experiment()
    assert first["run_id"] != second["run_id"]
    assert first["suite_hash"] == second["suite_hash"]
    assert first["schema_hash"] == second["schema_hash"]
    assert [item["prompt_hash"] for item in first["candidates"]] == [
        item["prompt_hash"] for item in second["candidates"]
    ]
    assert canonical_hash({"b": 2, "a": 1}) == canonical_hash({"a": 1, "b": 2})


def test_autoevals_schema_and_exact_contracts_are_exercised():
    result = load_experiment()
    structured = next(item for item in result["candidates"] if item["candidate_id"] == "structured")
    ambiguous = next(row for row in structured["rows"] if row["case_id"] == "EXT-017")
    assert ambiguous["schema_score"] == 1
    assert ambiguous["task_score"] > 0.8
    assert ambiguous["exact_score"] == 0
    assert ambiguous["review_reason"] == "expected_output_mismatch"


def test_review_correction_is_persisted_and_gate_recomputed(tmp_path):
    result = load_experiment()
    store = RunStore(tmp_path / "runs.sqlite3")
    store.save_run(result)
    review = next(
        item
        for item in store.list_reviews(result["run_id"], "open")
        if item["candidate_id"] == "structured" and item["case_id"] == "EXT-017"
    )
    expected = next(item for item in result["cases"] if item["case_id"] == "EXT-017")["expected"]
    resolved = store.resolve_review(review["review_id"], expected, "source lacks a reference date")
    updated = store.get_run(result["run_id"])
    structured = next(item for item in updated["candidates"] if item["candidate_id"] == "structured")
    assert resolved["status"] == "resolved"
    assert structured["summary"]["promoted"] is True
    assert updated["decision"]["winner"] == "structured"


def test_review_refuses_an_unsupported_correction(tmp_path):
    result = load_experiment()
    store = RunStore(tmp_path / "runs.sqlite3")
    store.save_run(result)
    review = next(item for item in store.list_reviews(result["run_id"], "open") if item["case_id"] == "EXT-017")
    with pytest.raises(ValueError, match="frozen expected"):
        store.resolve_review(
            review["review_id"],
            {
                "contact_name": "Mira Chen",
                "company": "Northstar Labs",
                "region": "eu",
                "intent": "integration",
                "urgency": "high",
                "follow_up": "2026-09-01",
            },
        )


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def provider_inputs():
    candidate = Candidate(
        candidate_id="remote",
        label="Remote",
        prompt="Return JSON",
        provider="openai-compatible",
        model="test-model",
        response_mode="structured",
    )
    case = EvalCase("A", "heldout", "clean", "Name: A", {"name": "A"})
    return candidate, case


def test_openai_compatible_adapter_retries_rate_limit_and_records_usage():
    calls = []

    def opener(request, timeout):
        calls.append((request.full_url, timeout))
        if len(calls) == 1:
            raise urllib.error.HTTPError(request.full_url, 429, "rate limited", {}, None)
        return FakeResponse(
            {
                "choices": [{"message": {"content": '{"name":"A"}'}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 5, "total_tokens": 17},
            }
        )

    adapter = OpenAICompatibleAdapter(
        OpenAICompatibleConfig(
            base_url="https://example.test/v1",
            api_key="test",
            model="test-model",
            max_retries=2,
            input_cost_per_million=1,
            output_cost_per_million=2,
        ),
        opener=opener,
        sleeper=lambda _: None,
    )
    result = adapter.generate(*provider_inputs())
    assert result.output == '{"name":"A"}'
    assert result.retry_count == 1
    assert result.rate_limit_count == 1
    assert result.total_tokens == 17
    assert result.cost_usd == pytest.approx(0.000022)


def test_openai_compatible_adapter_does_not_retry_permanent_failure():
    calls = []

    def opener(request, timeout):
        calls.append(request.full_url)
        raise urllib.error.HTTPError(request.full_url, 400, "bad request", {}, None)

    adapter = OpenAICompatibleAdapter(
        OpenAICompatibleConfig("https://example.test/v1", "test", "test-model", max_retries=2),
        opener=opener,
        sleeper=lambda _: None,
    )
    result = adapter.generate(*provider_inputs())
    assert result.output is None
    assert result.failure_class == "permanent"
    assert result.retry_count == 0
    assert len(calls) == 1


def test_api_runs_reviews_exports_and_serves_workbench(tmp_path):
    client = TestClient(create_app(tmp_path / "api.sqlite3"))
    assert client.get("/api/health").json()["status"] == "ready"
    page = client.get("/")
    assert page.status_code == 200
    assert "Comparison matrix" in page.text or "comparison matrix" in page.text
    response = client.post("/api/runs", json={})
    assert response.status_code == 201
    result = response.json()
    assert result["decision"]["winner"] == "repair"
    reviews = client.get("/api/reviews", params={"run_id": result["run_id"], "status": "open"}).json()
    assert any(item["candidate_id"] == "structured" and item["case_id"] == "EXT-017" for item in reviews)
    export = client.get("/api/reports/latest", params={"format": "csv"})
    assert export.status_code == 200
    assert "candidate_id,case_id" in export.text


def test_api_validates_in_memory_jsonl_and_rejects_missing_heldout(tmp_path):
    client = TestClient(create_app(tmp_path / "api.sqlite3"))
    valid = '{"case_id":"A","split":"heldout","input":"Name: A","expected":{"contact_name":"A"}}'
    assert client.post("/api/cases/validate", json={"format": "jsonl", "content": valid}).status_code == 200
    invalid = valid.replace("heldout", "train")
    response = client.post("/api/cases/validate", json={"format": "jsonl", "content": invalid})
    assert response.status_code == 422
    assert "heldout" in response.json()["detail"]


def test_optional_judge_fails_explicitly_without_configuration(tmp_path, monkeypatch):
    for name in ("PROOFGRID_JUDGE_BASE_URL", "PROOFGRID_JUDGE_API_KEY", "PROOFGRID_JUDGE_MODEL"):
        monkeypatch.delenv(name, raising=False)
    client = TestClient(create_app(tmp_path / "api.sqlite3"))
    response = client.post("/api/runs", json={"judge": True})
    assert response.status_code == 422
    assert "PROOFGRID_JUDGE_BASE_URL" in response.json()["detail"]
