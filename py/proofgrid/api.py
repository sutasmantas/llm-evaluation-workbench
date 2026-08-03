from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .observations import ObservationImportError, import_observation_bundles, parse_observation_bundle
from .providers import adapter_from_environment
from .runner import CaseImportError, adapters_for_candidates, execute_suite, load_candidates, load_cases, parse_cases
from .store import RunStore, result_to_csv


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SUITE = ROOT / "evals" / "proofgrid"
WEB_ROOT = ROOT / "proofgrid_web"


def _database_path() -> Path:
    return Path(os.getenv("PROOFGRID_DB_PATH", ROOT / ".proofgrid" / "runs.sqlite3"))


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((DEFAULT_SUITE / name).read_text(encoding="utf-8"))


class ImportRequest(BaseModel):
    format: Literal["jsonl", "csv"]
    content: str = Field(max_length=1_000_000)


class RunRequest(BaseModel):
    cases: list[dict[str, Any]] | None = Field(default=None, max_length=500)
    judge: bool = False


class ResolveRequest(BaseModel):
    corrected_output: dict[str, Any]
    note: str = Field(default="", max_length=500)


class ObservationImportRequest(BaseModel):
    bundles: list[dict[str, Any]] = Field(min_length=1, max_length=20)
    pricing: dict[str, Any] | None = None
    promotion: dict[str, Any] | None = None


class AnswerReviewRequest(BaseModel):
    reviewer: str = Field(min_length=1, max_length=120)
    first_useful_delta_index: int | None = Field(default=None, ge=0)
    scores: dict[str, int]
    note: str = Field(default="", max_length=1000)


def create_app(database_path: str | Path | None = None) -> FastAPI:
    app = FastAPI(title="ProofGrid", version="0.1.0")
    store = RunStore(database_path or _database_path())

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ready", "profile": "local-single-process"}

    @app.get("/api/suite")
    def suite() -> dict[str, Any]:
        cases = load_cases(DEFAULT_SUITE / "cases.jsonl")
        candidates = load_candidates(DEFAULT_SUITE / "candidates.json")
        return {
            "case_count": len(cases),
            "heldout_count": sum(case.split == "heldout" for case in cases),
            "categories": sorted({case.category for case in cases}),
            "candidates": [candidate.__dict__ for candidate in candidates],
            "promotion_rule": _load_json("promotion.json"),
        }

    @app.post("/api/cases/validate")
    def validate_import(request: ImportRequest) -> dict[str, Any]:
        try:
            cases = parse_cases(request.content, request.format)
        except CaseImportError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {
            "valid": True,
            "case_count": len(cases),
            "heldout_count": sum(case.split == "heldout" for case in cases),
            "case_ids": [case.case_id for case in cases],
        }

    @app.post("/api/runs", status_code=201)
    def run_suite(request: RunRequest | None = None) -> dict[str, Any]:
        if request and request.cases is not None:
            try:
                cases = parse_cases("\n".join(json.dumps(row) for row in request.cases), "jsonl")
            except CaseImportError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        else:
            cases = load_cases(DEFAULT_SUITE / "cases.jsonl")
        candidates = load_candidates(DEFAULT_SUITE / "candidates.json")
        try:
            result = execute_suite(
                cases=cases,
                candidates=candidates,
                schema=_load_json("schema.json"),
                promotion=_load_json("promotion.json"),
                adapters=adapters_for_candidates(candidates),
                judge=adapter_from_environment("PROOFGRID_JUDGE", "judge") if request and request.judge else None,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        store.save_run(result)
        return result

    @app.post("/api/observations/import", status_code=201)
    def import_observations(request: ObservationImportRequest) -> dict[str, Any]:
        try:
            bundles = [parse_observation_bundle(json.dumps(bundle)) for bundle in request.bundles]
            result = import_observation_bundles(
                bundles,
                pricing=request.pricing,
                promotion=request.promotion,
            )
        except ObservationImportError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        store.save_run(result)
        return result

    @app.get("/api/runs/latest")
    def latest_run() -> dict[str, Any]:
        result = store.latest_run()
        if result is None:
            raise HTTPException(status_code=404, detail="no evaluation run exists")
        return result

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, Any]:
        try:
            return store.get_run(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="run not found") from exc

    @app.get("/api/reviews")
    def reviews(run_id: str | None = None, status: Literal["open", "resolved"] | None = None) -> list[dict[str, Any]]:
        return store.list_reviews(run_id=run_id, status=status)

    @app.post("/api/reviews/{review_id}/resolve")
    def resolve(review_id: str, request: ResolveRequest) -> dict[str, Any]:
        try:
            return store.resolve_review(review_id, request.corrected_output, request.note)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="review not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/reviews/{review_id}/answer")
    def resolve_answer(review_id: str, request: AnswerReviewRequest) -> dict[str, Any]:
        try:
            return store.resolve_answer_review(
                review_id,
                reviewer=request.reviewer,
                first_useful_delta_index=request.first_useful_delta_index,
                scores=request.scores,
                note=request.note,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="review not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/reports/latest")
    def report(format: Literal["json", "csv"] = "json"):
        result = store.latest_run()
        if result is None:
            raise HTTPException(status_code=404, detail="no evaluation run exists")
        if format == "csv":
            return PlainTextResponse(
                result_to_csv(result),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={result['run_id']}.csv"},
            )
        return result

    if WEB_ROOT.is_dir():
        app.mount("/assets", StaticFiles(directory=WEB_ROOT), name="assets")

        @app.get("/", include_in_schema=False)
        def index() -> FileResponse:
            return FileResponse(WEB_ROOT / "index.html")

    return app
