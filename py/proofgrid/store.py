from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .observations import recompute_answer_decision, score_answer_review
from .runner import _evaluate_output, choose_winner, summarize_candidate


class RunStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    suite_hash TEXT NOT NULL,
                    result_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reviews (
                    review_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
                    candidate_id TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    original_output TEXT,
                    corrected_output TEXT,
                    reviewer TEXT,
                    assessment_json TEXT,
                    note TEXT,
                    updated_at TEXT NOT NULL,
                    UNIQUE(run_id, candidate_id, case_id)
                );
                """
            )
            columns = {row[1] for row in connection.execute("PRAGMA table_info(reviews)").fetchall()}
            if "reviewer" not in columns:
                connection.execute("ALTER TABLE reviews ADD COLUMN reviewer TEXT")
            if "assessment_json" not in columns:
                connection.execute("ALTER TABLE reviews ADD COLUMN assessment_json TEXT")

    def save_run(self, result: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO runs(run_id, created_at, suite_hash, result_json) VALUES (?, ?, ?, ?)",
                (result["run_id"], result["created_at"], result["suite_hash"], json.dumps(result, ensure_ascii=False)),
            )
            now = datetime.now(timezone.utc).isoformat()
            for candidate in result["candidates"]:
                for row in candidate["rows"]:
                    if row["needs_review"]:
                        review_id = f"{result['run_id']}:{candidate['candidate_id']}:{row['case_id']}"
                        connection.execute(
                            """
                            INSERT INTO reviews(
                                review_id, run_id, candidate_id, case_id, status, reason,
                                original_output, corrected_output, note, updated_at
                            ) VALUES (?, ?, ?, ?, 'open', ?, ?, NULL, NULL, ?)
                            """,
                            (
                                review_id,
                                result["run_id"],
                                candidate["candidate_id"],
                                row["case_id"],
                                row["review_reason"] or "manual_review",
                                row["output"],
                                now,
                            ),
                        )

    def get_run(self, run_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute("SELECT result_json FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        return json.loads(row["result_json"])

    def latest_run(self) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT result_json FROM runs ORDER BY created_at DESC LIMIT 1").fetchone()
        return json.loads(row["result_json"]) if row else None

    def list_reviews(self, run_id: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
        clauses = []
        params: list[str] = []
        if run_id:
            clauses.append("run_id = ?")
            params.append(run_id)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM reviews{where} ORDER BY updated_at DESC, review_id", params  # noqa: S608
            ).fetchall()
        return [dict(row) for row in rows]

    def resolve_review(self, review_id: str, corrected_output: dict[str, Any], note: str = "") -> dict[str, Any]:
        with self._connect() as connection:
            review = connection.execute("SELECT * FROM reviews WHERE review_id = ?", (review_id,)).fetchone()
            if review is None:
                raise KeyError(review_id)
            result_row = connection.execute(
                "SELECT result_json FROM runs WHERE run_id = ?", (review["run_id"],)
            ).fetchone()
            result = json.loads(result_row["result_json"])
            candidate = next(item for item in result["candidates"] if item["candidate_id"] == review["candidate_id"])
            row = next(item for item in candidate["rows"] if item["case_id"] == review["case_id"])
            serialized = json.dumps(corrected_output, ensure_ascii=False, sort_keys=True)
            scored = _evaluate_output(serialized, row["expected"], result["schema"])
            if scored["schema_score"] < 1:
                raise ValueError("corrected output does not satisfy the frozen schema")
            if scored["exact_score"] < 1:
                raise ValueError("corrected output does not match the frozen expected output")

            row.update(scored)
            row["output"] = serialized
            row["needs_review"] = False
            row["review_reason"] = None
            candidate["summary"] = summarize_candidate(candidate["rows"], result["promotion_rule"])
            promoted = [item["candidate_id"] for item in result["candidates"] if item["summary"]["promoted"]]
            result["decision"]["promoted_candidates"] = promoted
            result["decision"]["winner"] = choose_winner(result["candidates"])
            now = datetime.now(timezone.utc).isoformat()
            connection.execute(
                "UPDATE reviews SET status = 'resolved', corrected_output = ?, note = ?, updated_at = ? WHERE review_id = ?",
                (serialized, note, now, review_id),
            )
            connection.execute(
                "UPDATE runs SET result_json = ? WHERE run_id = ?",
                (json.dumps(result, ensure_ascii=False), review["run_id"]),
            )
        return {**dict(review), "status": "resolved", "corrected_output": serialized, "note": note, "updated_at": now}

    def resolve_answer_review(
        self,
        review_id: str,
        *,
        reviewer: str,
        first_useful_delta_index: int | None,
        scores: dict[str, Any],
        note: str = "",
    ) -> dict[str, Any]:
        with self._connect() as connection:
            review = connection.execute("SELECT * FROM reviews WHERE review_id = ?", (review_id,)).fetchone()
            if review is None:
                raise KeyError(review_id)
            if review["status"] != "open":
                raise ValueError("answer review is already resolved")
            result_row = connection.execute(
                "SELECT result_json FROM runs WHERE run_id = ?", (review["run_id"],)
            ).fetchone()
            result = json.loads(result_row["result_json"])
            if result.get("kind") != "answer_observation_comparison":
                raise ValueError("review does not belong to an answer observation run")
            candidate = next(item for item in result["candidates"] if item["candidate_id"] == review["candidate_id"])
            row = next(item for item in candidate["rows"] if item["case_id"] == review["case_id"])
            assessment = score_answer_review(
                row,
                reviewer=reviewer,
                first_useful_delta_index=first_useful_delta_index,
                scores=scores,
                note=note,
            )
            metadata = assessment["metadata"]
            row["review"] = assessment
            row["human_score"] = assessment["score"]
            row["human_pass"] = metadata["pass"]
            row["unsupported_claim_failure"] = metadata["scores"]["no_unsupported_claim"] == 0
            row["first_useful_ms"] = metadata["first_useful_ms"]
            row["needs_review"] = False
            row["review_reason"] = None
            recompute_answer_decision(result)
            serialized_assessment = json.dumps(assessment, ensure_ascii=False)
            now = datetime.now(timezone.utc).isoformat()
            connection.execute(
                """
                UPDATE reviews
                SET status = 'resolved', reviewer = ?, assessment_json = ?, note = ?, updated_at = ?
                WHERE review_id = ?
                """,
                (reviewer.strip(), serialized_assessment, note, now, review_id),
            )
            connection.execute(
                "UPDATE runs SET result_json = ? WHERE run_id = ?",
                (json.dumps(result, ensure_ascii=False), review["run_id"]),
            )
        return {
            **dict(review),
            "status": "resolved",
            "reviewer": reviewer.strip(),
            "assessment": assessment,
            "note": note,
            "updated_at": now,
        }


def result_to_csv(result: dict[str, Any]) -> str:
    import csv
    import io

    output = io.StringIO()
    fields = [
        "run_id",
        "candidate_id",
        "case_id",
        "split",
        "category",
        "schema_score",
        "task_score",
        "exact_score",
        "latency_ms",
        "first_delta_ms",
        "first_useful_ms",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "cost_usd",
        "retry_count",
        "rate_limit_count",
        "failure_class",
        "human_score",
        "human_pass",
        "unsupported_claim_failure",
        "needs_review",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for candidate in result["candidates"]:
        for row in candidate["rows"]:
            writer.writerow(
                {
                    "run_id": result["run_id"],
                    "candidate_id": candidate["candidate_id"],
                    **{field: row.get(field) for field in fields if field not in {"run_id", "candidate_id"}},
                }
            )
    return output.getvalue()
