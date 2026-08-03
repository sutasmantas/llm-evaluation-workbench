from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from .api import create_app
from .observations import ObservationImportError, import_observation_bundles, parse_observation_bundle
from .store import RunStore, result_to_csv


DIMENSIONS = {
    "addresses_question": 2,
    "uses_approved_context": 2,
    "no_unsupported_claim": 2,
    "concise_for_realtime": 2,
    "usable_structure": 2,
    "clarifies_when_needed": 2,
}


def observation(case_id: str, elapsed: float = 120) -> dict:
    return {
        "caseId": case_id,
        "split": "development",
        "category": "technical",
        "inputMode": "typed",
        "input": f"Question {case_id}",
        "contextIds": ["project-a"],
        "expected": {
            "points": ["Name the verified mechanism."],
            "mustNotClaim": ["An unsupported metric."],
            "answerFormat": "quick_cue",
        },
        "stream": [
            {"index": 0, "elapsedMs": 40, "text": "Grounded ", "cumulativeChars": 9},
            {"index": 1, "elapsedMs": elapsed, "text": "answer.", "cumulativeChars": 16},
        ],
        "outcome": "success",
        "output": "Grounded answer.",
        "timing": {"firstDeltaMs": 40, "completedMs": elapsed + 30},
        "usage": {
            "promptTokens": 100,
            "completionTokens": 10,
            "totalTokens": 110,
            "promptCacheHitTokens": 20,
            "promptCacheMissTokens": None,
        },
        "failure": None,
    }


def bundle(candidate_id: str, elapsed: float = 120) -> dict:
    observations = [observation("case-1", elapsed), observation("case-2", elapsed + 10)]
    return {
        "schema": "contextsidecar.answer-observations.v1",
        "capturedAt": "2026-08-03T08:00:00Z",
        "environment": {"platform": "win32 test", "node": "v22"},
        "candidate": {
            "id": candidate_id,
            "provider": "local-smoke",
            "model": f"model-{candidate_id}",
            "endpoint": "http://127.0.0.1/v1/chat/completions",
        },
        "capture": {
            "timeoutMs": 5000,
            "delayMs": 0,
            "casesSha256": "a" * 64,
            "replayContractSha256": "b" * 64,
            "contextPacksSha256": "c" * 64,
            "caseIds": [item["caseId"] for item in observations],
        },
        "observations": observations,
        "privacy": {"apiKeyPersisted": False, "fullContextPersisted": False},
    }


def parsed(candidate_id: str, elapsed: float = 120) -> dict:
    return parse_observation_bundle(json.dumps(bundle(candidate_id, elapsed)))


def test_observation_import_validates_privacy_order_and_stream_invariants():
    assert len(parsed("alpha")["observations"]) == 2

    wrong_order = bundle("alpha")
    wrong_order["capture"]["caseIds"].reverse()
    with pytest.raises(ObservationImportError, match="match observation order"):
        parse_observation_bundle(json.dumps(wrong_order))

    leaked = bundle("alpha")
    leaked["privacy"]["apiKeyPersisted"] = True
    with pytest.raises(ObservationImportError, match="schema error"):
        parse_observation_bundle(json.dumps(leaked))

    broken_stream = bundle("alpha")
    broken_stream["observations"][0]["stream"][1]["cumulativeChars"] = 99
    with pytest.raises(ObservationImportError, match="cumulativeChars"):
        parse_observation_bundle(json.dumps(broken_stream))

    credentialed_endpoint = bundle("alpha")
    credentialed_endpoint["candidate"]["endpoint"] = "https://user:pass@example.test/v1?key=secret"
    with pytest.raises(ObservationImportError, match="must not contain credentials"):
        parse_observation_bundle(json.dumps(credentialed_endpoint))

    inconsistent_usage = bundle("alpha")
    inconsistent_usage["observations"][0]["usage"]["totalTokens"] = 999
    with pytest.raises(ObservationImportError, match="totalTokens is inconsistent"):
        parse_observation_bundle(json.dumps(inconsistent_usage))


def test_imported_candidates_reuse_review_store_autoevals_score_and_decision(tmp_path):
    result = import_observation_bundles(
        [parsed("alpha", 100), parsed("beta", 180)],
        pricing={
            "alpha": {"input_per_million_usd": 1, "output_per_million_usd": 2, "source": "test-price"},
            "beta": {"input_per_million_usd": 2, "output_per_million_usd": 4, "source": "test-price"},
        },
    )
    assert result["kind"] == "answer_observation_comparison"
    assert result["decision"]["comparable_candidates"] is True
    assert result["decision"]["winner"] is None
    store = RunStore(tmp_path / "observations.sqlite3")
    store.save_run(result)
    reviews = store.list_reviews(result["run_id"], "open")
    assert len(reviews) == 4

    for review in reviews:
        resolved = store.resolve_answer_review(
            review["review_id"],
            reviewer="test-reviewer",
            first_useful_delta_index=1,
            scores=DIMENSIONS,
            note="The second delta makes the answer useful.",
        )
        assert resolved["assessment"]["name"] == "AnswerHumanRubric"
        assert resolved["assessment"]["score"] == 1

    updated = store.get_run(result["run_id"])
    assert updated["decision"]["winner"] == "alpha"
    assert updated["decision"]["provider_superiority_claim_allowed"] is False
    alpha = next(item for item in updated["candidates"] if item["candidate_id"] == "alpha")
    assert alpha["summary"]["case_pass_rate"] == 1
    assert alpha["summary"]["first_useful_p95_ms"] == 110
    assert alpha["summary"]["total_cost_usd"] == pytest.approx(0.00024)
    csv_report = result_to_csv(updated)
    assert "first_useful_ms" in csv_report
    assert "AnswerHumanRubric" not in csv_report

    with pytest.raises(ValueError, match="already resolved"):
        store.resolve_answer_review(
            reviews[0]["review_id"],
            reviewer="test-reviewer",
            first_useful_delta_index=1,
            scores=DIMENSIONS,
        )


def test_api_imports_observations_and_resolves_answer_review(tmp_path):
    client = TestClient(create_app(tmp_path / "api-observations.sqlite3"))
    response = client.post(
        "/api/observations/import",
        json={"bundles": [bundle("alpha"), bundle("beta", 180)]},
    )
    assert response.status_code == 201
    result = response.json()
    reviews = client.get("/api/reviews", params={"run_id": result["run_id"], "status": "open"}).json()
    resolved = client.post(
        f"/api/reviews/{reviews[0]['review_id']}/answer",
        json={
            "reviewer": "api-reviewer",
            "first_useful_delta_index": 1,
            "scores": DIMENSIONS,
            "note": "Observed evidence is sufficient.",
        },
    )
    assert resolved.status_code == 200
    assert resolved.json()["assessment"]["metadata"]["first_useful_ms"] is not None


def test_import_rejects_noncomparable_or_duplicate_candidates():
    first = parsed("alpha")
    mismatch = parsed("beta")
    mismatch["capture"]["contextPacksSha256"] = "d" * 64
    with pytest.raises(ObservationImportError, match="same frozen capture inputs"):
        import_observation_bundles([first, mismatch])
    with pytest.raises(ObservationImportError, match="candidate ids must be unique"):
        import_observation_bundles([first, first])

    altered_case = parsed("beta")
    altered_case["observations"][0]["expected"]["points"] = ["Different expected point."]
    with pytest.raises(ObservationImportError, match="identical case contracts"):
        import_observation_bundles([first, altered_case])

    with pytest.raises(ObservationImportError, match="unknown answer promotion fields"):
        import_observation_bundles([first], promotion={"unknown_gate": 1})
